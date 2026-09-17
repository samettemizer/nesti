# ProgressSpinner

ProgressSpinner is a process status indicator that supports both determinate and indeterminate modes.

## Indeterminate

An animated spinner indicating an indeterminate loading state is displayed by default when no value is provided.

```vue
<template>
    <div class="flex justify-center">
        <ProgressSpinner aria-label="loading" />
    </div>
</template>
```

## Determinate

Set a numeric value property to display a determinate progress indicator with a track and range.

```vue
<template>
    <div class="flex justify-center">
        <ProgressSpinner :value="75" />
    </div>
</template>
```

## Custom

ProgressSpinner can be customized with styling property like strokeWidth and the pt passthrough API.

```vue
<template>
    <div class="flex justify-center">
        <ProgressSpinner
            :strokeWidth="18"
            animationDuration=".5s"
            style="width: 50px; height: 50px"
            :pt="{
                circleTrack: { style: { stroke: 'transparent' } }
            }"
        />
    </div>
</template>
```

## Accessibility

Screen Reader ProgressSpinner components uses progressbar role. Value to describe the component can be defined using aria-labelledby and aria-label props. Keyboard Support Component does not include any interactive elements.

```vue
<template>
    <ProgressSpinner aria-label="Loading" />
</template>
```

## Progress Spinner API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| value | null \| number | null | Current progress value. When null, the component is in indeterminate mode. |
| min | number | 0 | Minimum value of the progress. |
| max | number | 100 | Maximum value of the progress. |
| strokeWidth | number | 4 | Width of the circle stroke. |
| animationDuration | string | '2s' | Duration of the rotate animation. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | ProgressSpinnerPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| circle | ProgressSpinnerPassThroughOptionType | Used to pass attributes to the circle SVG element. |
| circleTrack | ProgressSpinnerPassThroughOptionType | Used to pass attributes to the circle track element. |
| circleRange | ProgressSpinnerPassThroughOptionType | Used to pass attributes to the circle range element. |
| value | ProgressSpinnerPassThroughOptionType | Used to pass attributes to the value text element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-progressspinner | Class name of the root element |
| p-progressspinner-circle | Class name of the circle element |
| p-progressspinner-circle-track | Class name of the circle track element |
| p-progressspinner-circle-range | Class name of the circle range element |
| p-progressspinner-value | Class name of the value element |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| progressspinner.color.one | --p-progressspinner-color-one | Color one of root |
| progressspinner.color.two | --p-progressspinner-color-two | Color two of root |
| progressspinner.color.three | --p-progressspinner-color-three | Color three of root |
| progressspinner.color.four | --p-progressspinner-color-four | Color four of root |
