const DEFINITIONS = Object.freeze({
  GEOMETRY_NODE: { collection: "nodes", name: "节点", prefix: "N" },
  PHYSICAL_MEMBER: { collection: "physical_members", name: "构件", prefix: "M" },
  CONNECTION: { collection: "connections", name: "连接", prefix: "C" },
  SUPPORT: { collection: "supports", name: "支座", prefix: "S" },
  NODE_LOAD: { collection: "node_loads", name: "荷载", prefix: "L" },
});

const KIND_ALIASES = Object.freeze({
  GeometryNode: "GEOMETRY_NODE",
  PhysicalMember: "PHYSICAL_MEMBER",
  Connection: "CONNECTION",
  Support: "SUPPORT",
  NodeLoad: "NODE_LOAD",
});

function identity(item) { return item?.client_key || item?.id || null; }

export function createStudentLabelResolver(draft = {}) {
  const maps = {};
  for (const [kind, definition] of Object.entries(DEFINITIONS)) {
    const items = [...(draft?.[definition.collection] || [])].filter((item) => identity(item)).sort((left, right) => identity(left).localeCompare(identity(right)));
    maps[kind] = new Map(items.map((item, index) => {
      const explicit = typeof item.label === "string" && item.label.trim() ? item.label.trim() : `${definition.prefix}${index + 1}`;
      return [identity(item), `${definition.name} ${explicit}`];
    }));
  }
  return Object.freeze({
    label(kind, key) {
      const canonical = KIND_ALIASES[kind] || kind;
      const definition = DEFINITIONS[canonical];
      if (!definition) return "对象";
      return maps[canonical].get(key) || definition.name;
    },
  });
}
