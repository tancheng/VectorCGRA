# VectorCGRA xbar 配置参数说明

> 参考文件：`cgra/test/CgraRTL_test.py`、`noc/CrossbarRTL.py`、`tile/TileRTL.py`

---

## 一、基本参数（MESH 拓扑）

```
num_tile_inports  = 4   ← 邻居 tile 来的方向：N / S / W / E
num_tile_outports = 4   ← 发往邻居 tile 的方向：N / S / W / E
num_fu_inports    = 4   ← FU 的操作数入口数量
num_fu_outports   = 2   ← FU 的结果出口数量
num_routing_outports = num_tile_outports + num_fu_inports = 8
```

KingMesh 拓扑下 tile_ports = 8（8 个方向），其他参数类似。

---

## 二、routing_xbar_code[8]

### 作用
配置 **routing crossbar**（路由交叉开关）：决定每个输出端口从哪个输入取数据。

### 数组长度
`num_routing_outports = 8`

### 下标含义

| 下标 | 对应输出端口 |
|------|-------------|
| `[0]` | → NORTH 出口（发给北边 tile） |
| `[1]` | → SOUTH 出口（发给南边 tile） |
| `[2]` | → WEST 出口（发给西边 tile） |
| `[3]` | → EAST 出口（发给东边 tile） |
| `[4]` | → FU 操作数 0（FU_IN[0]） |
| `[5]` | → FU 操作数 1（FU_IN[1]） |
| `[6]` | → FU 操作数 2（FU_IN[2]） |
| `[7]` | → FU 操作数 3（FU_IN[3]） |

### 每个元素（TileInType）的值含义（1-indexed，0 = 不连接）

| 值 | 数据来源 |
|----|---------|
| `0` | 不连接（无数据输入） |
| `1` | 来自 **NORTH** 邻居发来的数据 |
| `2` | 来自 **SOUTH** 邻居发来的数据 |
| `3` | 来自 **WEST** 邻居发来的数据 |
| `4` | 来自 **EAST** 邻居发来的数据 |
| `5` | 来自本地寄存器堆 bank 0 |
| `6` | 来自本地寄存器堆 bank 1 |
| `7` | 来自本地寄存器堆 bank 2 |
| `8` | 来自本地寄存器堆 bank 3 |

---

## 三、fu_xbar_code[8]

### 作用
配置 **fu crossbar**（FU 结果交叉开关）：决定 FU 计算结果发送到哪个输出端口。

### 数组长度
同样为 `num_routing_outports = 8`，下标含义与 routing_xbar_code 完全相同。

### 每个元素（FuOutType）的值含义（1-indexed，0 = 不连接）

| 值 | 数据来源 |
|----|---------|
| `0` | 不连接（FU 结果不输出到此端口） |
| `1` | 来自 FU 输出 0（第一个结果） |
| `2` | 来自 FU 输出 1（第二个结果） |

---

## 四、两个 crossbar 的关系

```
邻居 tile 数据 (N/S/W/E)         寄存器堆数据
        │                              │
        └─────────┬────────────────────┘
                  ▼
         [ routing_crossbar ]
                  │
     ┌────────────┼────────────────────────┐
     ▼            ▼            ▼           ▼
  NORTH出      SOUTH出      WEST出      EAST出   ← 发往邻居 tile
                  │
     ┌────────────┼────────────────────────┐
     ▼            ▼            ▼           ▼
  FU_IN[0]   FU_IN[1]   FU_IN[2]   FU_IN[3]
                  │
                  ▼
              [ FU 计算 ]
                  │
          FU_OUT[0] / FU_OUT[1]
                  │
         [ fu_crossbar ]
                  │
     ┌────────────┼────────────────────────┐
     ▼            ▼            ▼           ▼
  NORTH出      SOUTH出      WEST出      EAST出   ← 发往邻居 tile（FU结果）
     ▼            ▼            ▼           ▼
  FU_IN[0]   FU_IN[1]   FU_IN[2]   FU_IN[3]   ← FU loopback
```

两个 crossbar 的 outport **下标顺序完全一致**：`[0..3]` 对应四个方向出口，`[4..7]` 对应四个 FU 操作数入口。

---

## 五、实际代码示例解读（systolic test, tile 7）

```python
CtrlType(OPT_MUL_CONST,
         fu_in_code,
         # routing_xbar_code
         [TileInType(0), TileInType(0), TileInType(0), TileInType(3),
          TileInType(3), TileInType(0), TileInType(0), TileInType(0)],
         # fu_xbar_code
         [FuOutType(0), FuOutType(1), FuOutType(0), FuOutType(0),
          FuOutType(0), FuOutType(0), FuOutType(0), FuOutType(0)])
```

### routing_xbar_code 解读

| 下标 | 值 | 含义 |
|------|----|------|
| `[0]` NORTH出 | 0 | 不向北转发 |
| `[1]` SOUTH出 | 0 | 不向南转发 |
| `[2]` WEST出 | 0 | 不向西转发 |
| `[3]` EAST出 | **3** | 把来自 WEST（tile 6）的数据转发到 EAST（tile 8） |
| `[4]` FU_IN[0] | **3** | 把来自 WEST（tile 6）的数据送入 FU 操作数 0 |
| `[5]` FU_IN[1] | 0 | 不输入 |
| `[6]` FU_IN[2] | 0 | 不输入 |
| `[7]` FU_IN[3] | 0 | 不输入 |

### fu_xbar_code 解读

| 下标 | 值 | 含义 |
|------|----|------|
| `[0]` NORTH出 | 0 | FU 结果不向北发送 |
| `[1]` SOUTH出 | **1** | FU 输出 0（乘法结果）发送给南边 tile（tile 4） |
| `[2]` WEST出 | 0 | 不向西发送 |
| `[3]` EAST出 | 0 | 不向东发送 |
| `[4..7]` FU_IN | 0 | 无 loopback |

---

## 六、default test 中的配置示例

```python
routing_xbar_code = [TileInType(0) for _ in range(num_routing_outports)]
# → 所有出口都设为 0，即不从任何邻居接收数据（从寄存器堆读取）

fu_xbar_code = [FuOutType(0) for _ in range(num_routing_outports)]
fu_xbar_code[num_tile_outports] = FuOutType(1)
# → fu_xbar_code[4] = FuOutType(1)，即 FU 输出 0 loopback 到 FU_IN[0]
```

---

## 七、快速记忆口诀

```
routing_xbar[0..3] = 四个方向出口（N/S/W/E），值=来自哪个方向的邻居（1=N,2=S,3=W,4=E）
routing_xbar[4..7] = FU 四个操作数入口，值同上
fu_xbar[0..3]      = 四个方向出口，值=用哪个 FU 输出（1或2）
fu_xbar[4..7]      = FU loopback，值=用哪个 FU 输出
值为 0 = 不连接
```
