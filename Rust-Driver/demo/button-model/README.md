# button-model

第七课 CP3：用结构体保存按键状态，用枚举表达按键事件。

## 运行

```bash
cargo run
```

## 输出

```text
pin 15: pressed
pin 15: held 20 ms
pin 15: released
```

## 为什么用枚举

三个 bool 可以组合出“同时 pressed 和 released”或“全 false”等非法状态；枚举只能三选一，`match` 又强制处理每个变体。

## 结构

- `ButtonState { pin: u8, pressed: bool }`：当前状态。
- `ButtonEvent`：`Pressed` / `Released` / `Held` 三个结构体变体。
- `ButtonState::new(pin)`：初始化为未按下。
- `ButtonState::update(pressed, ms)`：按本次采样返回事件。

`false/false` 的边界：课程版 `update` 仍返回 `Held`，这是避开 `Option` 的简化；严格模型应返回“无事件”，留到 `Option` 课。
