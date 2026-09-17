# Ripple

Ripple directive adds ripple effect to the host element.

## Configuration

To start with, Ripple needs to be enabled globally. See the Configuration API for details.

```vue
mounted() {
    this.$primevue.config.ripple = true;
}
```

## Default

Ripple is enabled by adding the v-ripple directive to the host element.

```vue
<template>
    <div class="flex flex-col items-center gap-4">
        <div v-ripple class="ripple-box">Default</div>
    </div>
</template>

<style scoped>
.ripple-box {
    display: flex;
    user-select: none;
    justify-content: center;
    align-items: center;
    padding: 2.625rem;
    font-weight: bold;
    font-size: 0.875rem;
    background: var(--p-content-background);
    border: 1px solid var(--p-content-border-color);
    border-radius: var(--p-content-border-radius);
}
<\/style>
```

## Custom

Default styling of the animation adds a shade of white. This can easily be customized using css that changes the color of p-ink element.

```vue
<template>
    <div class="flex justify-center gap-2">
        <div v-ripple class="box" style="border: 1px solid rgba(75, 175, 80, 0.3); --p-ripple-background: rgba(75, 175, 80, 0.3)">Green</div>
        <div v-ripple class="box" style="border: 1px solid rgba(255, 193, 6, 0.3); --p-ripple-background: rgba(255, 193, 6, 0.3)">Orange</div>
        <div v-ripple class="box" style="border: 1px solid rgba(156, 39, 176, 0.3); --p-ripple-background: rgba(156, 39, 176, 0.3)">Purple</div>
    </div>
</template>

<style scoped>
.box {
    padding: 1.75rem;
    border-radius: 10px;
    font-size: 0.875rem;
    width: 110px;
    text-align: center;
}
<\/style>
```

## Accessibility

Screen Reader Ripple element has the aria-hidden attribute as true so that it gets ignored by the screen readers. Keyboard Support Component does not include any interactive elements.

## Ripple API

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | RippleDirectivePassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | DirectiveHooks<any, any> | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-ink | Class name of the root element |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| ripple.background | --p-ripple-background | Background of root |
