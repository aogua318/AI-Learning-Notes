# button-model

第七课 CP3：用结构体保存按键状态，用枚举表达按键事件；第八课把“无事件”收口为 `Option`。

## 运行

```bash
cargo run
```

## 输出

```text
no event
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
- `ButtonState::update(pressed, ms) -> Option<ButtonEvent>`：按本次采样返回事件，没有事件时返回 `None`。

## 第八课收口：Option

第八课把 `update` 的返回类型改成 `Option<ButtonEvent>`：

- 上升沿 → `Some(Pressed)`；
- 下降沿 → `Some(Released)`；
- 已按下且仍按下 → `Some(Held)`；
- false/false（无事件）→ `None`。

`main` 用 `match` 同时处理 `Some(...)` 和 `None`，所以 false/false 不再伪装成 `Held`。完整任务见 [lessons/0008-option-and-error-handling.html](../../lessons/0008-option-and-error-handling.html)。
