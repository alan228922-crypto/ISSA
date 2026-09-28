import math

from django.core.exceptions import ValidationError
from django.db import models

from materials.models import Material, Section
from projects.models import Project


def _finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


class GeometryNode(models.Model):
    # 這些資料保存學生正在編輯的 physical draft，不是 Solver 直接使用的分析模型。
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="geometry_nodes")
    client_key = models.CharField(max_length=128)
    x_mm = models.FloatField()
    y_mm = models.FloatField()
    label = models.CharField(max_length=200, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["project", "client_key"], name="unique_geometry_node_client_key")]

    def clean(self):
        super().clean()
        if not _finite(self.x_mm) or not _finite(self.y_mm):
            raise ValidationError("INVALID_NUMERIC_VALUE")


class PhysicalMember(models.Model):
    # PhysicalMember 保存學生設計中的完整構件，之後才會被轉成 Solver 使用的分析構件。
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="physical_members")
    client_key = models.CharField(max_length=128)
    start_geometry_node = models.ForeignKey(GeometryNode, on_delete=models.SET_NULL, null=True, blank=True, related_name="starting_physical_members")
    end_geometry_node = models.ForeignKey(GeometryNode, on_delete=models.SET_NULL, null=True, blank=True, related_name="ending_physical_members")
    material = models.ForeignKey(Material, on_delete=models.SET_NULL, null=True, blank=True, related_name="physical_members")
    section = models.ForeignKey(Section, on_delete=models.SET_NULL, null=True, blank=True, related_name="physical_members")
    label = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["project", "client_key"], name="unique_physical_member_client_key")]

    def clean(self):
        super().clean()
        errors = {}
        if self.start_geometry_node_id and self.start_geometry_node.project_id != self.project_id:
            errors["start_geometry_node"] = "杆件端点必须属于同一项目。"
        if self.end_geometry_node_id and self.end_geometry_node.project_id != self.project_id:
            errors["end_geometry_node"] = "杆件端点必须属于同一项目。"
        if self.material_id and self.material.owner_user_id != self.project.owner_user_id:
            errors["material"] = "材料必须属于项目所有者。"
        if self.section_id and self.section.owner_user_id != self.project.owner_user_id:
            errors["section"] = "截面必须属于项目所有者。"
        if self.start_geometry_node_id and self.end_geometry_node_id:
            start, end = self.start_geometry_node, self.end_geometry_node
            if start.x_mm == end.x_mm and start.y_mm == end.y_mm:
                errors["end_geometry_node"] = "物理杆件不能为零长度。"
        if errors:
            raise ValidationError(errors)


class Connection(models.Model):
    # Connection 是明確的連接點；兩個位置看起來接近，不代表程式會自動把它們連在一起。
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="connections")
    client_key = models.CharField(max_length=128)
    geometry_node = models.ForeignKey(GeometryNode, on_delete=models.SET_NULL, null=True, blank=True, related_name="connections")
    participating_members = models.ManyToManyField(PhysicalMember, through="ConnectionParticipation", related_name="connections", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["project", "client_key"], name="unique_connection_client_key")]

    def clean(self):
        super().clean()
        if self.geometry_node_id and self.geometry_node.project_id != self.project_id:
            raise ValidationError({"geometry_node": "连接节点必须属于同一项目。"})


class ConnectionParticipation(models.Model):
    """One intended participation; a NULL member is a rebindable gap."""

    connection = models.ForeignKey(Connection, on_delete=models.CASCADE, related_name="participation_slots")
    member = models.ForeignKey(PhysicalMember, on_delete=models.SET_NULL, null=True, blank=True, related_name="participation_slots")
    position = models.PositiveIntegerField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=["connection", "position"], name="unique_connection_participation_position")]
        ordering = ["position"]

    def clean(self):
        super().clean()
        if self.member_id and self.connection_id and self.member.project_id != self.connection.project_id:
            raise ValidationError({"member": "参与构件必须属于同一项目。"})


class Support(models.Model):
    class Type(models.TextChoices):
        PINNED = "PINNED", "铰支座"
        ROLLER = "ROLLER", "滚动支座"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="supports")
    client_key = models.CharField(max_length=128)
    target_connection = models.ForeignKey(Connection, on_delete=models.SET_NULL, null=True, blank=True, related_name="supports")
    support_type = models.CharField(max_length=16, choices=Type.choices)
    restrained_axis = models.CharField(max_length=1, null=True, blank=True)

    # Support 記錄哪個方向被固定；之後再轉成 Solver 使用的自由度限制。

    def clean(self):
        super().clean()
        errors = {}
        if self.target_connection_id and self.target_connection.project_id != self.project_id:
            errors["target_connection"] = "支座连接必须属于同一项目。"
        if self.support_type == self.Type.PINNED and self.restrained_axis is not None:
            errors["restrained_axis"] = "铰支座不设置约束轴。"
        if self.support_type == self.Type.ROLLER and self.restrained_axis not in {"X", "Y"}:
            errors["restrained_axis"] = "滚动支座只能约束全局 X 或 Y 轴。"
        if errors:
            raise ValidationError(errors)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["project", "client_key"], name="unique_support_client_key")]


class NodeLoad(models.Model):
    # 荷載必須放在 Connection 上，這樣分析時才能知道力量作用在哪個節點。
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="node_loads")
    client_key = models.CharField(max_length=128)
    target_connection = models.ForeignKey(Connection, on_delete=models.SET_NULL, null=True, blank=True, related_name="node_loads")
    fx_N = models.FloatField()
    fy_N = models.FloatField()
    label = models.CharField(max_length=200, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["project", "client_key"], name="unique_node_load_client_key")]

    def clean(self):
        super().clean()
        errors = {}
        if self.target_connection_id and self.target_connection.project_id != self.project_id:
            errors["target_connection"] = "节点荷载连接必须属于同一项目。"
        if not _finite(self.fx_N) or not _finite(self.fy_N):
            errors["fx_N"] = "节点荷载必须是有限数值。"
        if errors:
            raise ValidationError(errors)
