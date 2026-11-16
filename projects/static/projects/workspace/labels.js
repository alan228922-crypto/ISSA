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

// SHA-256 is synchronous here because Canvas/ARIA label resolution is synchronous.
// This is an opaque display code, not a security/authentication primitive.
const DIGEST_CACHE = new Map();
const SHA256_K = [
  0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
  0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
  0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
  0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
  0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
  0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
  0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
  0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2,
];
function digestCode(key) {
  if (DIGEST_CACHE.has(key)) return DIGEST_CACHE.get(key);
  const bytes = new TextEncoder().encode(key);
  const padded = new Uint8Array(Math.ceil((bytes.length + 9) / 64) * 64);
  padded.set(bytes); padded[bytes.length] = 0x80;
  const view = new DataView(padded.buffer);
  view.setUint32(padded.length - 8, Math.floor(bytes.length / 0x20000000));
  view.setUint32(padded.length - 4, bytes.length * 8);
  const h = [0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19];
  const rotate = (x, n) => (x >>> n) | (x << (32 - n));
  for (let offset = 0; offset < padded.length; offset += 64) {
    const w = new Uint32Array(64);
    for (let i = 0; i < 16; i++) w[i] = view.getUint32(offset + i * 4);
    for (let i = 16; i < 64; i++) {
      const x = w[i-15], y = w[i-2];
      w[i] = w[i-16] + (rotate(x,7)^rotate(x,18)^(x>>>3)) + w[i-7] + (rotate(y,17)^rotate(y,19)^(y>>>10));
    }
    let [a,b,c,d,e,f,g,k] = h;
    for (let i = 0; i < 64; i++) {
      const t1 = (k + (rotate(e,6)^rotate(e,11)^rotate(e,25)) + ((e&f)^(~e&g)) + SHA256_K[i] + w[i]) >>> 0;
      const t2 = ((rotate(a,2)^rotate(a,13)^rotate(a,22)) + ((a&b)^(a&c)^(b&c))) >>> 0;
      [a,b,c,d,e,f,g,k] = [(t1+t2)>>>0,a,b,c,(d+t1)>>>0,e,f,g];
    }
    [a,b,c,d,e,f,g,k].forEach((x,i) => { h[i] = (h[i]+x)>>>0; });
  }
  // First 50 bits => exactly ten RFC4648 Base32 characters, independent of sets.
  let code = '';
  for (let i = 0; i < 10; i++) {
    let value = 0;
    for (let j = 0; j < 5; j++) { const bit = i*5+j; value = (value<<1) | ((h[Math.floor(bit/32)] >>> (31-bit%32))&1); }
    code += 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567'[value];
  }
  if (DIGEST_CACHE.size >= 10000) DIGEST_CACHE.clear();
  DIGEST_CACHE.set(key, code); return code;
}

const KEY_PREFIXES = { GEOMETRY_NODE:'node', PHYSICAL_MEMBER:'member', CONNECTION:'connection', SUPPORT:'support', NODE_LOAD:'load' };

export function createStudentLabelResolver(draft = {}) {
  const maps = {};
  for (const [kind, definition] of Object.entries(DEFINITIONS)) {
    const items = (draft?.[definition.collection] || []).filter((item) => typeof identity(item) === 'string' && identity(item));
    maps[kind] = new Map(items.map((item) => {
      const key = identity(item);
      const standard = key.match(new RegExp(`^${KEY_PREFIXES[kind]}-([1-9][0-9]*)$`));
      const code = `${definition.prefix}${standard ? standard[1] : `·${digestCode(key)}`}`;
      const name = `${definition.name} ${code}`;
      const description = typeof item.label === 'string' ? item.label.trim() : '';
      return [key, description ? `${description} · ${name}` : name];
    }));
  }
  return Object.freeze({
    label(kind, key) {
      const canonical = Object.hasOwn(KIND_ALIASES, kind) ? KIND_ALIASES[kind] : kind;
      const definition = Object.hasOwn(DEFINITIONS, canonical) ? DEFINITIONS[canonical] : null;
      if (!definition) return "对象";
      return maps[canonical].get(key) || definition.name;
    },
    analysisNode(id) {
      if (typeof id !== 'string') return '节点';
      if (id.startsWith('node:')) return maps.GEOMETRY_NODE.get(id.slice(5)) || '节点';
      if (id.startsWith('connection:')) return maps.CONNECTION.get(id.slice(11)) || '连接';
      const endpoint = id.match(/^free:(.*):(START|END)$/);
      if (endpoint) {
        const member = (draft.physical_members || []).find(row=>identity(row)===endpoint[1]);
        const nodeKey = endpoint[2] === 'START' ? member?.start_node_id ?? member?.start_node_client_key : member?.end_node_id ?? member?.end_node_client_key;
        return maps.GEOMETRY_NODE.get(nodeKey) || `${maps.PHYSICAL_MEMBER.get(endpoint[1]) || '构件'} ${endpoint[2] === 'START' ? '起点' : '终点'}`;
      }
      return '分析节点';
    },
    analysisMember(physicalKey, analysisKey) {
      const name = maps.PHYSICAL_MEMBER.get(physicalKey) || '构件';
      const segments = draft.analysis_member_mapping?.[physicalKey] || [];
      const index = segments.indexOf(analysisKey);
      return segments.length > 1 && index >= 0 ? `${name} · 分析段 ${index+1}` : name;
    },
  });
}
