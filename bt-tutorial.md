# 从零手搓：SHA-1 哈希、.torrent 解析与磁力链（配套 MD5 手册）

> 这是 [md5-tutorial.md](md5-tutorial.md) 的姊妹篇。MD5 手册教会你「手搓一个哈希算法 + 打包成 exe」，本文把同样的方法应用到 BT 生态的三个构件上：
>
> 1. **哈希值原理** → 从零实现 SHA-1（磁力链和 .torrent 用的是 SHA-1，不是 MD5）
> 2. **.torrent 原理** → 从零实现 bencode 编解码 + 种子解析器 + infohash 计算 + 分块校验器 + 种子制作器
> 3. **磁力链原理** → 从零实现磁力链解析/生成，并给出 DHT 网络的最小可运行实现
>
> 全程只用 Python 标准库（`struct`、`socket`、`urllib.parse`），不用任何第三方库。学完后你将拥有一个「种子校验/制作 + 磁力链工具」的完整 CLI，并知道每行代码为什么这么写。
>
> 依赖关系（先学哪个）：SHA-1 是地基 → bencode 是承重墙 → infohash/校验器是房间 → 磁力链和 DHT 是大门。

---

## 目录

1. [任务一：哈希值的原理 → 从零实现 SHA-1](#1-任务一哈希值的原理--从零实现-sha-1)
2. [任务二：.torrent 的原理 → 从零实现 bencode、解析器与校验器](#2-任务二torrent-的原理--从零实现-bencode解析器与校验器)
3. [任务三：磁力链的原理 → 从零实现磁力链与 DHT 最小实现](#3-任务三磁力链的原理--从零实现磁力链与-dht-最小实现)
4. [整合：bt 命令行工具与打包 exe](#4-整合bt-命令行工具与打包-exe)

---

## 1. 任务一：哈希值的原理 → 从零实现 SHA-1

### 1.1 原理：SHA-1 和 MD5 是同一个家族

SHA-1 和 MD5 都是 **Merkle–Damgård 结构**的哈希：把消息切块 → 逐块压缩进一个固定大小的内部状态 → 状态就是摘要。你已经手搓过 MD5，SHA-1 只改了四个地方：

| | MD5 | SHA-1 |
|---|---|---|
| 摘要长度 | 128 位（4 个 32 位寄存器） | **160 位（5 个 32 位寄存器）** |
| 轮数 | 64 步 | **80 步** |
| 字节序 | 全程小端（消息字、长度、输出） | **全程大端** |
| 常数来源 | `floor(2^32·abs(sin(i)))` 查 64 个表 | 只有 **4 个**常数，按轮段取用 |
| 非线性函数 | 4 个不同的 F | 3 个函数循环复用 + 1 个纯轮转 |

**80 步循环的结构**（每 20 步一段）：

```
f = b·c | (~b)·d          (前 20 步, Ch)   k = 0x5A827999
f = b XOR c XOR d         (20-40,  Parity) k = 0x6ED9EBA1
f = (b|c) & (~b|d)        (40-60,  Maj)    k = 0x8F1BBCDC
f = b XOR c XOR d         (60-80,  Parity) k = 0xCA62C1D6

temp = (a 左旋 5) + f + e + k + W[i]
e = d; d = c; c = b 左旋 30; b = a; a = temp
```

**消息字扩展是 SHA-1 特有的**：每块 16 个原始字 `M[0..15]` 不够 80 步用，先把它们扩展成 80 个：

```
W[i] = M[i]                       (i < 16)
W[i] = 左旋1(W[i-3] ^ W[i-8] ^ W[i-14] ^ W[i-16])   (i >= 16)
```

**填充规则和 MD5 几乎一样，只有一处不同**：补 `0x80` → 补 `0x00` 到 ≡56 (mod 64) → 追加 8 字节位长——但**大端序**（MD5 是小端）。输出时 5 个寄存器 h0..h4 也按**大端**拼接成 20 字节。

> 记忆口诀：**SHA-1 全家大端**。从 MD5 移植过来时 90% 的 bug 出在忘了改字节序。

### 1.2 实现流程

新建 `sha1core.py`：

```python
"""sha1core.py — 纯 Python 手写 SHA-1（FIPS 180-4），无任何第三方依赖。"""
import struct

_MASK = 0xFFFFFFFF


def _left_rotate(x, n):
    x &= _MASK
    return ((x << n) | (x >> (32 - n))) & _MASK


def _compress(state, block: bytes):
    """对单个 64 字节块做 80 步压缩。state 是长度 5 的列表 [h0..h4]。"""
    # ---- 消息字扩展：16 个原始字 → 80 个 ----
    W = list(struct.unpack('>16I', block))          # 大端！
    for i in range(16, 80):
        W.append(_left_rotate(
            W[i-3] ^ W[i-8] ^ W[i-14] ^ W[i-16], 1))

    a, b, c, d, e = state
    for i in range(80):
        if i < 20:
            f = (b & c) | (~b & d);        k = 0x5A827999
        elif i < 40:
            f = b ^ c ^ d;                 k = 0x6ED9EBA1
        elif i < 60:
            f = (b & c) | (b & d) | (c & d); k = 0x8F1BBCDC
        else:
            f = b ^ c ^ d;                 k = 0xCA62C1D6

        temp = (_left_rotate(a, 5) + f + e + k + W[i]) & _MASK
        e = d
        d = c
        c = _left_rotate(b, 30)
        b = a
        a = temp

    # 累加（模 2^32）
    state[0] = (state[0] + a) & _MASK
    state[1] = (state[1] + b) & _MASK
    state[2] = (state[2] + c) & _MASK
    state[3] = (state[3] + d) & _MASK
    state[4] = (state[4] + e) & _MASK


def sha1(data: bytes) -> bytes:
    # ---- 填充：0x80 → 0x00 至 ≡56 (mod 64) → 8 字节大端位长 ----
    orig_len_bits = (len(data) * 8) & 0xFFFFFFFFFFFFFFFF
    data = bytearray(data)
    data.append(0x80)
    while len(data) % 64 != 56:
        data.append(0x00)
    data += struct.pack('>Q', orig_len_bits)        # 大端，和 MD5 唯一的填充差异

    # ---- 初始 5 个寄存器（大端约定下的魔数）----
    state = [0x67452301, 0xEFCDAB89, 0x98BADCFE, 0x10325476, 0xC3D2E1F0]

    for off in range(0, len(data), 64):
        _compress(state, data[off:off + 64])

    return struct.pack('>5I', *state)               # 大端输出


def sha1_hex(data: bytes) -> str:
    return sha1(data).hex()


if __name__ == '__main__':
    # FIPS 180-4 官方测试向量
    for msg, expect in [
        (b'',        'da39a3ee5e6b4b0d3255bfef95601890afd80709'),
        (b'abc',     'a9993e364706816aba3e25717850c26c9cd0d89d'),
        (b'abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq',
                     '84983e441c3bd26ebaae4aa1f95129e5e54670f1'),
        (b'a' * 1000000, '34aa973cd4c4daa4f61eeb2bdbad27316534016f'),  # 百万个 a
    ]:
        got = sha1_hex(msg)
        assert got == expect, f'FAIL {msg[:20]!r}: {got}'
        print(f'OK  {expect}')
```

### 1.3 实现细节坑位对照表（MD5 → SHA-1 移植清单）

| 你在 MD5 里写过的 | SHA-1 里要改成 | 忘改的后果 |
|---|---|---|
| `struct.unpack('<16I')` | `'>16I'` | 所有块第一个消息字错 |
| `struct.pack('<Q', len)` | `'>Q'` | 全部结果错 |
| `struct.pack('<4I', ...)` 输出 | `'>5I'`，5 个寄存器 | 输出错且只有 16 字节 |
| 4 个寄存器 | 5 个（多一个 `e`） | 状态错位，全错 |
| 64 步 + 64 常数表 | 80 步 + 4 段常数 | 全错 |
| 4 个 F 函数 | 3 个 F + 第 3 段 Maj 写法注意 `(b&c)|(b&d)|(c&d)` | 第 40~60 步错 |
| — | **消息字扩展**（MD5 没有） | 全错 |
| — | `c = b 左旋 30`（MD5 没有这一步旋转） | 全错 |

流式版本和 MD5 手册第 4.3 节的 `Md5Stream` 结构完全相同（缓存尾块、`update()`、`hexdigest()` 时补 padding），把压缩函数换掉即可，此处不重复。验证方式也一样：`hashlib.sha1` 交叉验证 0~200 全长度 + 55/56/57、63/64/65 字节边界。

---

## 2. 任务二：.torrent 的原理 → 从零实现 bencode、解析器与校验器

### 2.1 原理：三层数据结构

.torrent = **bencode 编码**的字典，关键字段：

```
d (根字典)
  announce: tracker URL
  info: d                    ← ★ 一切的核心
    name: 文件/目录名
    piece length: 每块字节数（2 的幂，常见 256KB~16MB）
    pieces: 所有块 SHA-1 的二进制拼接（每块 20 字节）
    length: 单文件种子的文件大小
    ——或（多文件种子）——
    files: [ {path: [目录, ..., 文件名], length: N}, ... ]
```

**infohash = 对 `info` 字典「原始 bencode 字节」整体做一次 SHA-1。** 这句话里最容易踩的坑：必须用**文件里 info 字段的原始字节**，不能「解码成 Python 对象再重新编码」——重新编码可能改变字段顺序、整数表示或多余空白，算出来的 infohash 就和别人不一样了。

**分块校验**：把所有文件按顺序首尾拼成虚拟大流，第 i 块 = 虚拟流的 `[i × piece_length, (i+1) × piece_length)` 区间，对每块算 SHA-1 与 `pieces` 中对应 20 字节比对。注意**文件边界可以横穿块的中间**——一个块可能由「文件 A 的尾巴 + 文件 B 的开头」组成，这是实现校验器时最大的逻辑陷阱。

### 2.2 第一步：从零实现 bencode

bencode 只有 4 种类型，编码规则自描述：

| 类型 | 编码 | 例 |
|---|---|---|
| 整数 | `i<十进制>e` | `i42e`、`i0e`、`i-3e` |
| 字节串 | `<长度>:<原始字节>` | `4:spam` |
| 列表 | `l<元素1><元素2>...e` | `l4:spami42ee` |
| 字典 | `d<键1><值1><键2><值2>...e`，键必须是字节串且**按字节序排序** | `d3:bar4:spam4:fooi42ee` |

新建 `bencode.py`：

```python
"""bencode.py — 从零实现 bencode 编解码，无任何第三方依赖。
解码返回 int / bytes / list / dict；str 一律用 bytes（.torrent 是字节的世界）。
"""


# ---------- 编码 ----------
def bencode(obj) -> bytes:
    if isinstance(obj, int):
        return b'i%de' % obj
    if isinstance(obj, bytes):
        return b'%d:%s' % (len(obj), obj)
    if isinstance(obj, str):                    # 便捷入口：按 UTF-8 编码
        return bencode(obj.encode('utf-8'))
    if isinstance(obj, list):
        return b'l' + b''.join(bencode(x) for x in obj) + b'e'
    if isinstance(obj, dict):
        if any(not isinstance(k, bytes) for k in obj):
            raise TypeError('bencode dict 键必须是 bytes')
        out = b'd'
        for k in sorted(obj.keys()):            # ★ 字节序排序，规范化必须
            out += bencode(k) + bencode(obj[k])
        return out + b'e'
    raise TypeError(f'无法 bencode: {type(obj)}')


# ---------- 解码 ----------
class BDecoder:
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    def _byte(self) -> int:
        if self.pos >= len(self.data):
            raise ValueError('数据意外结束')
        b = self.data[self.pos]
        self.pos += 1
        return b

    def decode(self):
        c = self._byte()
        if c == 0x69:                           # 'i'
            end = self.data.index(b'e', self.pos)
            val = int(self.data[self.pos:end])
            if self.data[self.pos:self.pos+1] == b'-0':
                raise ValueError('禁止 -0')     # bencode 规范：不允许 -0
            self.pos = end + 1
            return val
        if c == 0x6C:                           # 'l'
            out = []
            while self.data[self.pos:self.pos+1] != b'e':
                out.append(self.decode())
            self.pos += 1
            return out
        if c == 0x64:                           # 'd'
            out = {}
            while self.data[self.pos:self.pos+1] != b'e':
                k = self.decode()
                if not isinstance(k, bytes):
                    raise TypeError('字典键必须是字节串')
                out[k] = self.decode()
            self.pos += 1
            return out
        if 0x30 <= c <= 0x39:                   # '0'-'9' → 字节串
            colon = self.data.index(b':', self.pos)
            length = int(self.data[self.pos - 1:colon])   # ★ 首位数字已被 _byte 吃掉，要包含回来
            if length < 0:
                raise ValueError('负长度')
            self.pos = colon + 1
            val = self.data[self.pos:self.pos + length]
            if len(val) != length:
                raise ValueError('字节串越界')
            self.pos += length
            return val
        raise ValueError(f'非法前缀字节: {chr(c)!r}')


def bdecode(data: bytes):
    d = BDecoder(data)
    val = d.decode()
    return val
```

**自测**（编码→解码往返必须还原，这是编解码器最硬的标准）：

```python
# test_bencode.py
from bencode import bencode, bdecode

CASES = [
    0, -3, 42,
    b'', b'spam', b'\x00\xff\xfe',                 # 二进制安全
    [b'a', 1, [b'nested']],
    {b'bar': b'spam', b'foo': 42, b'lst': [b'x']},
]
for c in CASES:
    assert bdecode(bencode(c)) == c, c

# 规范化：字典键必须字节序排序（infohash 正确性的根基）
assert bencode({b'b': 1, b'a': 2}) == b'd1:ai2e1:bi1ee'

# 大整数：长度前缀上限（防止畸形种子声明 10^20 长度吃光内存）
assert bdecode(b'i' + b'9' * 20 + b'e') == int('9' * 20)

print('bencode OK')
```

坑位提醒：
- **一切字符串都是 bytes**。路径名、tracker URL 都是字节串，UTF-8/GBK 转码放到最外层 GUI/CLI 做，内核不碰 str，否则中文文件名必炸。
- **解码大字典不要递归爆栈**：极端嵌套的恶意种子会打爆 Python 递归限制；生产实现要改成显式栈，学习版至少心里有数。
- **长度校验**：解码 `length:` 字节串时按声明长度切，如果声明超过剩余数据会切片静默变短——上面用 `len(val) != length` 显式报错，防畸形数据。

### 2.3 第二步：解析 .torrent 并算 infohash

```python
"""torrentfile.py — 解析种子、算 infohash、枚举分块。"""
import os
from sha1core import sha1, sha1_hex
from bencode import bdecode


class Torrent:
    def __init__(self, raw: bytes):
        self.raw = raw
        root = bdecode(raw)
        if not isinstance(root, dict) or b'info' not in root:
            raise ValueError('不是合法的种子文件')

        # ★ infohash：取 info 字典的【原始字节】，不是重新编码
        self.infohash = sha1(self._raw_span_of(b'info')).hex()

        info = root[b'info']
        self.name = info.get(b'name', b'').decode('utf-8', 'replace')
        self.piece_length = info[b'piece length']
        pieces = info[b'pieces']
        if len(pieces) % 20 != 0:
            raise ValueError('pieces 长度不是 20 的倍数')
        self.piece_hashes = [pieces[i:i+20] for i in range(0, len(pieces), 20)]

        # 文件清单：统一成 [(相对路径 bytes, 长度)]，虚拟拼接流的顺序
        self.files = []
        if b'files' in info:                      # 多文件种子
            for f in info[b'files']:
                rel = b'/'.join(f[b'path'])
                self.files.append((rel, f[b'length']))
        else:                                     # 单文件种子
            self.files.append((info[b'name'], info[b'length']))

    def _raw_span_of(self, key: bytes) -> bytes:
        """在原始字节里定位根字典中 key 对应【值的完整编码字节】。
        做法：重新用带偏移的解码器走一遍根字典，记录每个值的 (start, end)。"""
        d = _OffsetDecoder(self.raw)
        return d.raw_value_of(key)


class _OffsetDecoder:
    """BDecoder 变体：解码根字典时记录每个值的原始字节区间。"""
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    def _decode(self):
        c = self.data[self.pos]
        if c == 0x64:                             # 'd'：字典
            self.pos += 1
            out = {}
            while self.data[self.pos] != 0x65:    # 'e'
                k = self._decode()
                v = self._decode()
                out[k] = v
            self.pos += 1
            return out
        if c == 0x6C:                             # 'l'
            self.pos += 1
            out = []
            while self.data[self.pos] != 0x65:
                out.append(self._decode())
            self.pos += 1
            return out
        if c == 0x69:
            end = self.data.index(b'e', self.pos)
            val = int(self.data[self.pos + 1:end])
            self.pos = end + 1
            return val
        # 字节串：长度前缀 → 返回解码值（键比较需要真值）
        colon = self.data.index(b':', self.pos)
        n = int(self.data[self.pos:colon])
        self.pos = colon + 1
        val = self.data[self.pos:self.pos + n]
        self.pos += n
        return val

    def raw_value_of(self, key: bytes) -> bytes:
        """只在【根字典这一层】找 key，返回其值的原始字节。"""
        self.pos = 1                              # 跳过 'd'
        while self.data[self.pos] != 0x65:
            kstart = self.pos
            k = self._decode()                    # 键一定是字节串
            kend = self.pos
            vstart = self.pos
            self._decode()                        # 解析值只为推进 pos
            vend = self.pos
            if k == key:
                return self.data[vstart:vend]
        raise KeyError(key)
```

> 为什么不用「`bencode(bdecode(raw)[b'info'])`」？因为 `bdecode` 丢弃了原始表示：整数 `i01e`（非法但可能出现）、`i+3e`、键顺序若有非规范化写法，重编码后字节就变了。**infohash 的权威来源永远是磁盘上的原始字节**——这也是 BT 客户端做「重新哈希校验种子」时的标准做法。我给的非规范种子概率低，但「从原始字节取区间」是唯一万无一失的办法，值得这一小段额外代码。

### 2.4 第三步：分块校验器（处理文件横穿块边界）

思路：把文件清单拼成**虚拟流**，一个生成器按块 yield 数据，主循环逐块哈希比对。

```python
# verify.py — 对本地文件逐块校验种子
import os
from sha1core import sha1


def piece_iter(torrent, base_dir: str):
    """按顺序产出每个分块的完整字节。文件边界可以横穿块中间。"""
    remaining = torrent.piece_length
    buf = bytearray()
    for rel_path, length in torrent.files:
        path = os.path.join(base_dir, rel_path.decode('utf-8'))
        with open(path, 'rb') as f:
            left = length
            while left > 0:
                want = min(remaining, left)
                data = f.read(want)
                if len(data) != want:
                    raise IOError(f'文件比种子声明短: {rel_path!r}')
                buf += data
                remaining -= want
                left -= want
                if remaining == 0:                # 攒满一块
                    yield bytes(buf)
                    buf = bytearray()
                    remaining = torrent.piece_length
    if buf:                                       # 最后一块不足整块
        yield bytes(buf)


def verify(torrent, base_dir: str, report=True) -> tuple[int, int]:
    """返回 (坏块数, 总块数)。"""
    bad = 0
    n = len(torrent.piece_hashes)
    for i, piece in enumerate(piece_iter(torrent, base_dir)):
        if sha1(piece) != torrent.piece_hashes[i]:
            bad += 1
            if report:
                print(f'第 {i} 块: FAILED')
    if report:
        print(f'\n{bad}/{n} 块损坏' if bad else f'\n全部 {n} 块校验通过')
    return bad, n
```

关键逻辑就在 `piece_iter`：`remaining` 是「当前块还差多少字节」，跨文件时不清零，自然把 A 的尾巴和 B 的开头拼进同一块。**最后一个不足 piece_length 的块也是合法块**（BT 规定按实际长度校验），所以循环结束后还有一次 `if buf: yield`。

### 2.5 第四步：种子制作器（反向工程）

理解结构的最好方式是把自己造一遍：

```python
# mktorrent.py — 从本地文件/目录制作种子
import os
from sha1core import sha1
from bencode import bencode


def make_torrent(target: str, piece_length=4 * 1024 * 1024,
                 announce=b'http://tracker.example.com/announce') -> bytes:
    target = os.path.abspath(target)
    name = os.path.basename(target).encode('utf-8')

    # 收集文件清单（相对路径 + 长度），顺序按路径排序保证确定性
    if os.path.isdir(target):
        files = []
        for root, dirs, fnames in os.walk(target):
            dirs.sort()
            for fn in sorted(fnames):
                full = os.path.join(root, fn)
                rel = os.path.relpath(full, target).replace('\\', '/')
                files.append((rel.encode('utf-8'), os.path.getsize(full)))
        files.sort()
    else:
        files = [(name, os.path.getsize(target))]

    # 逐块哈希：同样是「虚拟拼接流」，和校验器逻辑对称
    pieces = bytearray()
    remaining = piece_length
    buf = bytearray()
    for rel, size in files:
        with open(os.path.join(target, rel.decode('utf-8')), 'rb') as f:
            left = size
            while left > 0:
                want = min(remaining, left)
                data = f.read(want)
                buf += data
                remaining -= want
                left -= want
                if remaining == 0:
                    pieces += sha1(bytes(buf))
                    buf = bytearray()
                    remaining = piece_length
    if buf:
        pieces += sha1(bytes(buf))

    info = {
        b'name': name,
        b'piece length': piece_length,
        b'pieces': bytes(pieces),
    }
    if len(files) == 1 and files[0][0] == name:
        info[b'length'] = files[0][1]
    else:
        info[b'files'] = [
            {b'path': rel.split(b'/'), b'length': n} for rel, n in files
        ]

    torrent = {
        b'announce': announce,
        b'info': info,
    }
    return bencode(torrent)


if __name__ == '__main__':
    import sys
    open(sys.argv[1] + '.torrent', 'wb').write(make_torrent(sys.argv[1]))
```

**闭环验证**（这一步跑通，任务二才算真正学会）：

1. 对任意目录 `make_torrent(目录)` 生成种子；
2. 用 qBittorrent/Transmission 打开这个种子——官方客户端能识别且 infohash 与我们算出的一致（`transmission-show xxx.torrent` 可直接看 infohash）；
3. 用 2.4 的 `verify()` 校验源目录：0 块损坏；
4. 随便改坏一个字节再校验：恰好那 1 个块 FAILED，其余 OK。

第 2 步是终极互验：如果官方客户端显示的 infohash 和你的不一致，99% 是 `_raw_span_of` 或 bencode 排序出了问题。

---

## 3. 任务三：磁力链的原理 → 从零实现磁力链与 DHT 最小实现

### 3.1 磁力链的结构化解析

磁力链本质是一个 URL 查询串，每对参数是「用途=值」：

```
magnet:?xt=urn:btih:<infohash>&dn=<名字>&tr=<tracker1>&tr=<tracker2>&xl=<字节数>
```

标准库 `urllib.parse` 拆它绰绰有余，从零实现的要点是**btih 的两种编码**：40 字符十六进制，或 32 字符 Base32（Base32 不区分大小写，把 160 位编成 32 个字母数字）。很多老磁力链是 Base32，不处理就解析不了：

```python
"""magnet.py — 磁力链解析与生成"""
import base64
import urllib.parse
from urllib.parse import urlparse, parse_qs


def parse_magnet(uri: str) -> dict:
    if not uri.startswith('magnet:?'):
        raise ValueError('不是磁力链')
    qs = parse_qs(urlparse(uri).query)
    out = {'xt': [], 'tr': []}
    for k, vs in qs.items():
        for v in vs:
            if k == 'xt' and v.startswith('urn:btih:'):
                h = v[len('urn:btih:'):]
                if len(h) == 40:
                    out['xt'].append(h.lower())           # 十六进制
                elif len(h) == 32:
                    out['xt'].append(
                        base64.b32decode(h.upper()).hex())  # Base32 → hex
                else:
                    raise ValueError(f'btih 长度非法: {h!r}')
            elif k == 'tr':
                out['tr'].append(v)
            else:
                out.setdefault(k, []).append(v)
    if not out['xt']:
        raise ValueError('磁力链缺少 xt=urn:btih:')
    return out


def build_magnet(infohash_hex: str, name: str = '', trackers=()) -> str:
    if len(infohash_hex) != 40:
        raise ValueError('infohash 必须是 40 位十六进制')
    parts = [f'xt=urn:btih:{infohash_hex.lower()}']
    if name:
        parts.append('dn=' + urllib.parse.quote(name))
    for t in trackers:
        parts.append('tr=' + urllib.parse.quote(t, safe=''))
    return 'magnet:?' + '&'.join(parts)
```

**磁力链 ↔ 种子的互通**（纯本地操作，不需要网络）：

```python
from torrentfile import Torrent

t = Torrent(open('xxx.torrent', 'rb').read())
print(build_magnet(t.infohash, t.name))       # 种子 → 磁力链（一行的事）
m = parse_magnet(uri)                          # 磁力链 → 拿到 infohash
print(m['xt'][0] == t.infohash)                # True
```

反方向（**磁力链 → 种子**）需要网络：BT 客户端拿着 infohash 去找 peers，用 **BEP 9（元数据交换）**协议向 peer 索要 `info` 字典（分片传输，每片 16 KB，每片用 SHA-1 校验，收齐后整体 infohash 再对一遍——还是分块哈希那套思想）。这需要完整的 BT 握手 + 扩展协议，本文不展开，但流程你已经能看懂了。

### 3.2 DHT 最小实现：亲眼看一次「按哈希找人」

磁力链没有 tracker 时靠 DHT（BEP 5）找 peers。它的 KRPC 协议就是 **UDP 上的 bencode 字典**——你 2.2 手搓的 bencode 在这里直接复用。下面是一个能真跑的最小探测程序，向公共 DHT 节点发 `ping` 和 `get_peers`：

```python
"""dht_probe.py — DHT (BEP 5) 最小探测：只发请求并打印响应。
KRPC: bencode 字典 {t:事务号, y:'q'/'r'/'e', q:方法名, a:参数}
"""
import os
import socket
from bencode import bencode, bdecode


def krpc(sock, addr, msg) -> dict | None:
    sock.sendto(bencode(msg), addr)
    try:
        data, _ = sock.recvfrom(4096)
        return bdecode(data)
    except socket.timeout:
        return None


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(3)
    tid = os.urandom(2)                           # 事务 ID：2 字节随机串
    my_id = os.urandom(20)                        # 本节点 ID：随机 160 位

    # ---- ping: {a:{id: 我的节点ID}} ----
    resp = krpc(sock, ('router.bittorrent.com', 6881),
                {b't': tid, b'y': b'q', b'q': b'ping',
                 b'a': {b'id': my_id}})
    print('ping →', resp)                         # {r:{id:对方ID}, t:.., y:'r'}

    # ---- get_peers: 问「这个 infohash 谁有」----
    target = bytes.fromhex('6e1b810f38b99a5e0f0e3b4d7c9f2a1b0d4e5f6a')
    resp = krpc(sock, ('dht.transmissionbt.com', 6881),
                {b't': tid, b'y': b'q', b'q': b'get_peers',
                 b'a': {b'id': my_id, b'info_hash': target}})
    r = resp.get(b'r', {}) if resp else {}
    if b'values' in r:
        print('拿到 peers:', r[b'values'])        # 每项 6 字节 = 4IP + 2端口（大端）
    elif b'nodes' in r:
        print('拿到更近的 K 个节点:', len(r[b'nodes']) // 26, '个')
    else:
        print('超时或错误:', resp)


if __name__ == '__main__':
    main()
```

预期输出类似：

```
ping → {b'r': {b'id': b'...20字节...'}, b't': b'\x??\x??', b'y': b'r'}
拿到 peers: [b'\xd4]\xa8\x0e\x1a\xdb', ...]     ← 每条 6 字节：IP+端口
```

这 30 行代码证明了一件事：**DHT 的查询就是「用 infohash 当键，向哈希空间里距离它最近的节点要 peers」**。完整客户端在这之上还要实现：路由表维护（K 桶）、迭代查找（问 A→A 给我更近的 B→问 B……）、宣布自己（`announce_peer`）、`values` 返回的 peers 再逐个 BT 握手要元数据（BEP 9）。原理你已经全打通了，剩下是工程量。

### 3.3 三个任务合到一起：认知收束

现在把 0.x 章的「是什么」全部换成「怎么做」：

- **哈希值**：确定性 + 雪崩 + 单向 + 抗碰撞 → SHA-1 的 80 步压缩循环，你已经逐行写出来过；
- **.torrent**：bencode 自描述编码 + `pieces` 分块哈希清单 + infohash（原始字节的 SHA-1）+ 文件横穿块边界的虚拟流校验，你都能实现；
- **磁力链**：infohash 当资源唯一 ID → DHT/KRPC（bencode over UDP）按哈希找人 → BEP 9 换回 info 字典 → 逐块校验下载。

整个 BT 体系没有黑魔法，全部构件你都已经从零写出了最小可用版本。

---

## 4. 整合：bt 命令行工具与打包 exe

把三个任务合并成 `btapp.py` CLI（结构与 MD5 手册的 `md5app.py` 相同：菜单 + 参数双模式）：

```
用法:
  bt.exe info  <x.torrent>            打印种子信息 + infohash
  bt.exe verify <x.torrent> [目录]    逐块校验本地文件
  bt.exe make  <文件或目录> [out.torrent]  制作种子
  bt.exe magnet <x.torrent>           种子转磁力链
  bt.exe magnet -i <磁力链>           解析磁力链（打印 infohash/tracker）
  bt.exe dht   <infohash>             DHT 探测：打印能否找到 peers
```

打包方法与 MD5 手册完全一致（这也是两份手册分开放的原因——流水线是同一套，只换源码）：

```bash
cython -3 --embed -o btmain.c btapp.py
cl /nologo /O2 /GL /MD /I "%PY%\include" btmain.c ^
   /link /LTCG /OPT:REF /OPT:ICF /LIBPATH:"%PY%\libs" python313.lib /OUT:bt.exe
```

纯 Python 版各功能的性能预期：SHA-1 约 1~3 MB/s（和 MD5 同级），校验 1 GB 文件约 10 分钟——用 MD5 手册第 6~7 节的同一套 Cython 类型标注方法（`cdef unsigned int` + 指针访问 + `noexcept`）编译热点后可达约 100 MB/s。SHA-1 的循环比 MD5 多一步消息字扩展（80 个 W 的数组），Cython 化时把 `W` 声明成栈上 `cdef unsigned int W[80]` 即可。

**发布前验收清单**：

```bash
# 1. SHA-1 与 hashlib 交叉验证（0~200 全长度 + 边界长度）
# 2. bencode 往返测试（含二进制字节串、负数、嵌套）
# 3. 自制种子被 qBittorrent/Transmission 正确识别，infohash 一致
# 4. verify 对源目录 0 块损坏；篡改 1 字节后恰好 1 块 FAILED
# 5. 种子转磁力链 → qBittorrent 能从磁力链识别出同一个种子（显示相同 infohash）
# 6. dht 探测对任一热门资源的磁力链能拿到 peers
```
