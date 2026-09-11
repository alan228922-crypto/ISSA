from accounts.models import User


def can_manage_material(actor,material):
    """所有权在服务端判断；Manager 默认不能修改学生材料。"""
    return actor.role==User.Role.DEVELOPER or actor.id==material.owner_user_id
