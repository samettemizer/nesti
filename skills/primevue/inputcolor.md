# InputColor

InputColor is a composable color picker component.

## Basic

InputColor is a composable color picker with area, slider, swatch, and input sub-components.

```vue
<template>
    <div class="flex justify-center">
        <div class="max-w-xs mx-auto space-y-3 w-xs">
            <InputColor v-model="value" :format="format === 'hex' ? 'rgba' : format">
                <InputColorArea>
                    <InputColorAreaBackground />
                    <InputColorAreaHandle />
                </InputColorArea>
                <div class="flex items-center gap-2">
                    <div class="flex-1 space-y-1 mr-1">
                        <InputColorSlider>
                            <InputColorTransparencyGrid />
                            <InputColorSliderTrack />
                            <InputColorSliderHandle />
                        </InputColorSlider>
                        <InputColorSlider channel="alpha">
                            <InputColorTransparencyGrid />
                            <InputColorSliderTrack />
                            <InputColorSliderHandle />
                        </InputColorSlider>
                    </div>
                    <div class="flex items-center gap-2">
                        <InputColorSwatch>
                            <InputColorTransparencyGrid />
                            <InputColorSwatchBackground />
                        </InputColorSwatch>
                        <InputColorEyeDropper severity="secondary" variant="outlined">
                            <template #icon>
                                <EyeDropper />
                            </template>
                        </InputColorEyeDropper>
                    </div>
                </div>
                <div class="flex items-center gap-2">
                    <Select v-model="format" :options="formatOptions" optionLabel="label" optionValue="value" class="w-full md:w-26" />
                    <div class="flex-1">
                        <InputGroup>
                            <InputColorInput v-if="format === 'hex'" fluid channel="hex" />
                            <InputColorInput v-else-if="format === 'oklcha'" fluid channel="css" />
                            <template v-else-if="format === 'rgba'">
                                <InputColorInput fluid channel="red" />
                                <InputColorInput fluid channel="green" />
                                <InputColorInput fluid channel="blue" />
                                <InputColorInput fluid channel="alpha" />
                            </template>
                            <template v-else-if="format === 'hsba'">
                                <InputColorInput fluid channel="hue" />
                                <InputColorInput fluid channel="saturation" />
                                <InputColorInput fluid channel="brightness" />
                                <InputColorInput fluid channel="alpha" />
                            </template>
                            <template v-else-if="format === 'hsla'">
                                <InputColorInput fluid channel="hue" />
                                <InputColorInput fluid channel="saturation" />
                                <InputColorInput fluid channel="lightness" />
                                <InputColorInput fluid channel="alpha" />
                            </template>
                        </InputGroup>
                    </div>
                </div>
            </InputColor>
        </div>
    </div>
</template>

<script setup>
import EyeDropper from '@primeicons/vue/eye-dropper';
import { ref } from 'vue';

const value = ref('#276def');
const format = ref('hex');
const formatOptions = [
    { label: 'HEX', value: 'hex' },
    { label: 'RGBA', value: 'rgba' },
    { label: 'HSBA', value: 'hsba' },
    { label: 'HSLA', value: 'hsla' },
    { label: 'OKLCHA', value: 'oklcha' }
];
<\/script>
```

## With Popover

InputColor can be used inside a Popover, with a color swatch as the trigger.

```vue
<template>
    <div class="flex items-center justify-center">
        <InputColor v-model="value">
            <InputColorSwatch @click="(e) => op.toggle(e)" style="cursor: pointer">
                <InputColorTransparencyGrid />
                <InputColorSwatchBackground />
            </InputColorSwatch>
            <Popover ref="op">
                <div class="w-72 p-3 space-y-3">
                    <InputColorArea>
                        <InputColorAreaBackground />
                        <InputColorAreaHandle />
                    </InputColorArea>
                    <InputColorSlider>
                        <InputColorTransparencyGrid />
                        <InputColorSliderTrack />
                        <InputColorSliderHandle />
                    </InputColorSlider>
                    <InputColorSlider channel="alpha">
                        <InputColorTransparencyGrid />
                        <InputColorSliderTrack />
                        <InputColorSliderHandle />
                    </InputColorSlider>
                    <div class="flex items-center gap-2">
                        <InputColorInput channel="hex" class="flex-1" />
                        <InputColorEyeDropper iconOnly severity="secondary" variant="outlined">
                            <template #icon>
                                <EyeDropper />
                            </template>
                        </InputColorEyeDropper>
                    </div>
                </div>
            </Popover>
        </InputColor>
    </div>
</template>

<script setup>
import EyeDropper from '@primeicons/vue/eye-dropper';
import { ref } from 'vue';

const value = ref('#0099ff');
const op = ref(null);
<\/script>
```

## Vertical Slider

Sliders support vertical orientation, displayed alongside the color area.

```vue
<template>
    <div class="flex items-center justify-center">
        <InputColor v-model="value" format="hsba">
            <div class="flex gap-4 max-w-md w-full mx-auto">
                <InputColorArea class="flex-1">
                    <InputColorAreaBackground />
                    <InputColorAreaHandle />
                </InputColorArea>
                <InputColorSlider orientation="vertical">
                    <InputColorTransparencyGrid />
                    <InputColorSliderTrack />
                    <InputColorSliderHandle />
                </InputColorSlider>
                <InputColorSlider channel="saturation" orientation="vertical">
                    <InputColorTransparencyGrid />
                    <InputColorSliderTrack />
                    <InputColorSliderHandle />
                </InputColorSlider>
                <InputColorSlider channel="brightness" orientation="vertical">
                    <InputColorTransparencyGrid />
                    <InputColorSliderTrack />
                    <InputColorSliderHandle />
                </InputColorSlider>
                <InputColorSlider channel="alpha" orientation="vertical">
                    <InputColorTransparencyGrid />
                    <InputColorSliderTrack />
                    <InputColorSliderHandle />
                </InputColorSlider>
            </div>
        </InputColor>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const value = ref('');
<\/script>
```

## Controlled

Demonstrates tracking color value changes during interaction and when interaction ends.

```vue
<template>
    <div class="flex justify-center">
        <div class="max-w-xs mx-auto space-y-3 w-xs">
            <div class="text-center font-mono text-sm text-surface-500">onValueChange: {{ value }}</div>
            <div class="text-center font-mono text-sm text-surface-500">onValueChangeEnd: {{ endValue }}</div>
            <InputColor v-model="value" @value-change="onValueChange" @value-change-end="onValueChangeEnd">
                <InputColorArea>
                    <InputColorAreaBackground />
                    <InputColorAreaHandle />
                </InputColorArea>
                <div class="flex items-center gap-2">
                    <div class="flex-1 space-y-1 mr-1">
                        <InputColorSlider>
                            <InputColorTransparencyGrid />
                            <InputColorSliderTrack />
                            <InputColorSliderHandle />
                        </InputColorSlider>
                        <InputColorSlider channel="alpha">
                            <InputColorTransparencyGrid />
                            <InputColorSliderTrack />
                            <InputColorSliderHandle />
                        </InputColorSlider>
                    </div>
                    <InputColorSwatch>
                        <InputColorTransparencyGrid />
                        <InputColorSwatchBackground />
                    </InputColorSwatch>
                    <InputColorEyeDropper severity="secondary" variant="outlined">
                        <template #icon>
                            <EyeDropper />
                        </template>
                    </InputColorEyeDropper>
                </div>
                <InputColorInput fluid channel="hex" />
            </InputColor>
        </div>
    </div>
</template>

<script setup>
import EyeDropper from '@primeicons/vue/eye-dropper';
import { ref } from 'vue';

const value = ref('#000000');
const endValue = ref('#000000');

const onValueChange = (event) => {
    value.value = event.color;
};

const onValueChangeEnd = (event) => {
    endValue.value = event.color;
};
<\/script>
```

## Advanced

Advanced color picker with per-format channel sliders, input groups for RGBA, HSBA, HSLA, OKLCH channels, and a CSS output.

```vue
<template>
    <div class="flex justify-center">
        <div class="max-w-xs mx-auto space-y-3">
            <Select v-model="format" :options="formatOptions" optionLabel="label" optionValue="value" fluid />
            <InputColor v-model="value" :format="format">
                <InputColorArea>
                    <InputColorAreaBackground />
                    <InputColorAreaHandle />
                </InputColorArea>
                <InputColorSlider>
                    <InputColorTransparencyGrid />
                    <InputColorSliderTrack />
                    <InputColorSliderHandle />
                </InputColorSlider>
                <template v-if="format === 'rgba'">
                    <InputColorSlider channel="red">
                        <InputColorTransparencyGrid />
                        <InputColorSliderTrack />
                        <InputColorSliderHandle />
                    </InputColorSlider>
                    <InputColorSlider channel="green">
                        <InputColorTransparencyGrid />
                        <InputColorSliderTrack />
                        <InputColorSliderHandle />
                    </InputColorSlider>
                    <InputColorSlider channel="blue">
                        <InputColorTransparencyGrid />
                        <InputColorSliderTrack />
                        <InputColorSliderHandle />
                    </InputColorSlider>
                </template>
                <template v-else-if="format === 'hsba'">
                    <InputColorSlider channel="saturation">
                        <InputColorTransparencyGrid />
                        <InputColorSliderTrack />
                        <InputColorSliderHandle />
                    </InputColorSlider>
                    <InputColorSlider channel="brightness">
                        <InputColorTransparencyGrid />
                        <InputColorSliderTrack />
                        <InputColorSliderHandle />
                    </InputColorSlider>
                </template>
                <template v-else-if="format === 'hsla'">
                    <InputColorSlider channel="saturation">
                        <InputColorTransparencyGrid />
                        <InputColorSliderTrack />
                        <InputColorSliderHandle />
                    </InputColorSlider>
                    <InputColorSlider channel="lightness">
                        <InputColorTransparencyGrid />
                        <InputColorSliderTrack />
                        <InputColorSliderHandle />
                    </InputColorSlider>
                </template>
                <InputColorSlider channel="alpha">
                    <InputColorTransparencyGrid />
                    <InputColorSliderTrack />
                    <InputColorSliderHandle />
                </InputColorSlider>
                <div class="flex gap-2">
                    <InputColorSwatch>
                        <InputColorTransparencyGrid />
                        <InputColorSwatchBackground />
                    </InputColorSwatch>
                    <InputColorEyeDropper severity="secondary" variant="outlined">
                        <template #icon>
                            <EyeDropper />
                        </template>
                    </InputColorEyeDropper>
                    <InputColorInput channel="hex" class="flex-1" />
                </div>
                <InputGroup>
                    <FloatLabel variant="in">
                        <InputColorInput channel="red" type="text" size="small" />
                        <label>Red</label>
                    </FloatLabel>
                    <FloatLabel variant="in">
                        <InputColorInput channel="green" type="text" size="small" />
                        <label>Green</label>
                    </FloatLabel>
                    <FloatLabel variant="in">
                        <InputColorInput channel="blue" type="text" size="small" />
                        <label>Blue</label>
                    </FloatLabel>
                    <FloatLabel variant="in">
                        <InputColorInput channel="alpha" type="text" size="small" />
                        <label>Alpha</label>
                    </FloatLabel>
                </InputGroup>
                <InputGroup>
                    <FloatLabel variant="in">
                        <InputColorInput channel="hue" type="text" size="small" />
                        <label>Hue</label>
                    </FloatLabel>
                    <FloatLabel variant="in">
                        <InputColorInput channel="saturation" type="text" size="small" />
                        <label>Saturation</label>
                    </FloatLabel>
                    <FloatLabel variant="in">
                        <InputColorInput channel="brightness" type="text" size="small" />
                        <label>Brightness</label>
                    </FloatLabel>
                    <FloatLabel variant="in">
                        <InputColorInput channel="alpha" type="text" size="small" />
                        <label>Alpha</label>
                    </FloatLabel>
                </InputGroup>
                <InputGroup>
                    <FloatLabel variant="in">
                        <InputColorInput channel="hue" type="text" size="small" />
                        <label>Hue</label>
                    </FloatLabel>
                    <FloatLabel variant="in">
                        <InputColorInput channel="saturation" type="text" size="small" />
                        <label>Saturation</label>
                    </FloatLabel>
                    <FloatLabel variant="in">
                        <InputColorInput channel="lightness" type="text" size="small" />
                        <label>Lightness</label>
                    </FloatLabel>
                    <FloatLabel variant="in">
                        <InputColorInput channel="alpha" type="text" size="small" />
                        <label>Alpha</label>
                    </FloatLabel>
                </InputGroup>
                <InputGroup>
                    <FloatLabel variant="in">
                        <InputColorInput channel="L" type="text" size="small" />
                        <label>Lightness</label>
                    </FloatLabel>
                    <FloatLabel variant="in">
                        <InputColorInput channel="C" type="text" size="small" />
                        <label>Chroma</label>
                    </FloatLabel>
                    <FloatLabel variant="in">
                        <InputColorInput channel="H" type="text" size="small" />
                        <label>Hue</label>
                    </FloatLabel>
                    <FloatLabel variant="in">
                        <InputColorInput channel="alpha" type="text" size="small" />
                        <label>Alpha</label>
                    </FloatLabel>
                </InputGroup>
                <InputGroup>
                    <InputGroupAddon>CSS</InputGroupAddon>
                    <InputColorInput channel="css" type="text" fluid />
                </InputGroup>
            </InputColor>
        </div>
    </div>
</template>

<script setup>
import EyeDropper from '@primeicons/vue/eye-dropper';
import { ref } from 'vue';

const value = ref('#ff0000');
const format = ref('hsla');
const formatOptions = [
    { label: 'RGBA', value: 'rgba' },
    { label: 'HSBA', value: 'hsba' },
    { label: 'HSLA', value: 'hsla' },
    { label: 'OKLCHA', value: 'oklcha' }
];
<\/script>
```

## Forms

InputColor integrates seamlessly with the PrimeVue Forms library.

```vue
<template>
    <div class="flex justify-center">
        <Form v-slot="$form" :resolver="resolver" :initialValues="initialValues" @submit="onFormSubmit" class="flex flex-col gap-4">
            <div class="flex flex-col items-center gap-2">
                <div class="max-w-xs mx-auto space-y-3 w-xs">
                    <InputColor name="color" format="hex">
                        <InputColorArea>
                            <InputColorAreaBackground />
                            <InputColorAreaHandle />
                        </InputColorArea>
                        <div class="flex items-center gap-2">
                            <div class="flex-1 space-y-1 mr-1">
                                <InputColorSlider>
                                    <InputColorTransparencyGrid />
                                    <InputColorSliderTrack />
                                    <InputColorSliderHandle />
                                </InputColorSlider>
                                <InputColorSlider channel="alpha">
                                    <InputColorTransparencyGrid />
                                    <InputColorSliderTrack />
                                    <InputColorSliderHandle />
                                </InputColorSlider>
                            </div>
                            <InputColorSwatch>
                                <InputColorTransparencyGrid />
                                <InputColorSwatchBackground />
                            </InputColorSwatch>
                            <InputColorEyeDropper severity="secondary" variant="outlined">
                                <template #icon>
                                    <EyeDropper />
                                </template>
                            </InputColorEyeDropper>
                        </div>
                        <InputColorInput fluid channel="hex" />
                    </InputColor>
                </div>
                <Message v-if="$form.color?.invalid" severity="error" size="small" variant="simple">{{ $form.color.error?.message }}</Message>
            </div>
            <Button type="submit" severity="secondary">Submit</Button>
        </Form>
    </div>
</template>

<script setup>
import EyeDropper from '@primeicons/vue/eye-dropper';
import { ref } from 'vue';
import { zodResolver } from '@primevue/forms/resolvers/zod';
import { useToast } from "primevue/usetoast";
import { z } from 'zod';

const toast = useToast();
const initialValues = ref({
    color: null
});
const resolver = ref(zodResolver(
    z.object({
        color: z.union([z.string(), z.literal(null)]).refine((value) => value !== null, { message: 'Color is required.' })
    })
));

const onFormSubmit = ({ valid }) => {
    if (valid) {
        toast.add({ severity: 'success', summary: 'Form is submitted.', life: 3000 });
    }
};
<\/script>
```

## Color Class

The Color class is the base class for all color classes. It provides the basic functionality for all color classes. clone() : Clones the color. toString(format) : Converts the color to a string. toFormat(format) : Converts the color to a specific format. toJSON() : Converts the color to a JSON object. getChannelRange(channel) : Returns the range of the channel. getFormat() : Returns the format of the color. getChannels() : Returns the channels of the color. getChannelValue(channel) : Returns the value of the channel. getSpaceAxes(xyChannels) : Returns the axes of the color. incChannelValue(channel, step) : Increments the value of the channel by the step. decChannelValue(channel, step) : Decrements the value of the channel by the step. setChannelValue(channel, value) : Returns a new color with the value of the channel changed.

## Accessibility

InputColorArea Screen Reader The area handle has role="slider" with aria-roledescription="2d slider" . It includes aria-label describing the two axes (e.g., "saturation and brightness"), aria-valuemin , aria-valuemax , aria-valuenow , and aria-valuetext describing the current channel values. Keyboard Support Key Function tab Moves focus to the area handle. right arrow Moves the area handle to the right. left arrow Moves the area handle to the left. up arrow Moves the area handle up. down arrow Moves the area handle down. InputColorSlider Screen Reader The slider handle has role="slider" with aria-label , aria-valuemin , aria-valuemax , aria-valuenow , and aria-valuetext describing the current channel value. Keyboard Support Key Function tab Moves focus to the slider handle. up arrow left arrow Decrements the slider value. down arrow right arrow Increments the slider value.

## Input Color API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| modelValue | any | - | Value of the component, paired with  `v-model` . Format follows  format . |
| defaultValue | any | - | The default value for the component. Used in uncontrolled mode and as the initial value when integrated with PrimeVue Forms. |
| name | string | - | The name attribute for the component, used to identify it within a form. |
| format | any | 'hsba' | Output format for  `update:modelValue`  and channel inputs reading the  `css`  channel. |
| disabled | boolean | false | When present, disables the component and all child interactions. |
| invalid | boolean | false | When present, it specifies that the component should have invalid state style. |
| formControl | Record<string, any> | - | Form control object, typically provided by parent form context. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | InputColorPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-inputcolor | Class name of the root element |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| inputcolor.border.color | --p-inputcolor-border-color | Shared inset border color (area background, slider track, swatch background) |
| inputcolor.area.border.radius | --p-inputcolor-area-border-radius | Border radius of area |
| inputcolor.slider.border.radius | --p-inputcolor-slider-border-radius | Border radius of slider |
| inputcolor.slider.size | --p-inputcolor-slider-size | Size of slider (horizontal height / vertical width) |
| inputcolor.handle.size | --p-inputcolor-handle-size | Size of handle (area and slider) |
| inputcolor.handle.border.color | --p-inputcolor-handle-border-color | Border color of handle |
| inputcolor.handle.border.width | --p-inputcolor-handle-border-width | Border width of handle |
| inputcolor.handle.shadow | --p-inputcolor-handle-shadow | Shadow of handle |
| inputcolor.handle.transition.duration | --p-inputcolor-handle-transition-duration | Transition duration of handle |
| inputcolor.handle.focus.ring.border.width | --p-inputcolor-handle-focus-ring-border-width | Focus ring border width of handle |
| inputcolor.handle.focus.ring.border.color | --p-inputcolor-handle-focus-ring-border-color | Focus ring border color of handle |
| inputcolor.handle.focus.ring.outline.width | --p-inputcolor-handle-focus-ring-outline-width | Focus ring outline width of handle |
| inputcolor.handle.focus.ring.outline.color | --p-inputcolor-handle-focus-ring-outline-color | Focus ring outline color of handle |
| inputcolor.handle.focus.ring.outline.offset | --p-inputcolor-handle-focus-ring-outline-offset | Focus ring outline offset of handle |
| inputcolor.transparency.grid.color | --p-inputcolor-transparency-grid-color | Color of transparency grid (checker pattern) |
| inputcolor.transparency.grid.background | --p-inputcolor-transparency-grid-background | Background of transparency grid (checker base) |
| inputcolor.transparency.grid.tile.size | --p-inputcolor-transparency-grid-tile-size | Tile size of transparency grid |
| inputcolor.swatch.size | --p-inputcolor-swatch-size | Size of swatch |
| inputcolor.swatch.border.radius | --p-inputcolor-swatch-border-radius | Border radius of swatch |

## Input Color Area API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| as | string \| Component | DIV | Use to change the HTML tag of root element. |
| asChild | boolean | false | When enabled, it changes the default rendered element for the one passed as a child element. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | InputColorAreaPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-inputcolor-area | Class name of the root element |

## Input Color Area Background API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| as | string \| Component | DIV | Use to change the HTML tag of root element. |
| asChild | boolean | false | When enabled, it changes the default rendered element for the one passed as a child element. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | InputColorAreaBackgroundPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-inputcolor-area-background | Class name of the root element |

## Input Color Area Handle API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| as | string \| Component | DIV | Use to change the HTML tag of root element. |
| asChild | boolean | false | When enabled, it changes the default rendered element for the one passed as a child element. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | InputColorAreaHandlePassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-inputcolor-area-handle | Class name of the root element |

## Input Color Slider API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| channel | any | 'hue' | Channel this slider drives. |
| orientation | InputColorSliderOrientation | 'horizontal' | Slider orientation. |
| disabled | boolean | false | Disable just this slider (in addition to the parent  `InputColor.disabled` ). |
| as | string \| Component | DIV | Use to change the HTML tag of root element. |
| asChild | boolean | false | When enabled, it changes the default rendered element for the one passed as a child element. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | InputColorSliderPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-inputcolor-slider | Class name of the root element |

## Input Color Slider Handle API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| as | string \| Component | DIV | Use to change the HTML tag of root element. |
| asChild | boolean | false | When enabled, it changes the default rendered element for the one passed as a child element. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | InputColorSliderHandlePassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-inputcolor-slider-handle | Class name of the root element |

## Input Color Slider Track API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| as | string \| Component | DIV | Use to change the HTML tag of root element. |
| asChild | boolean | false | When enabled, it changes the default rendered element for the one passed as a child element. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | InputColorSliderTrackPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-inputcolor-slider-track | Class name of the root element |

## Input Color Swatch API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| as | string \| Component | DIV | Use to change the HTML tag of root element. |
| asChild | boolean | false | When enabled, it changes the default rendered element for the one passed as a child element. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | InputColorSwatchPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-inputcolor-swatch | Class name of the root element |

## Input Color Swatch Background API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| as | string \| Component | DIV | Use to change the HTML tag of root element. |
| asChild | boolean | false | When enabled, it changes the default rendered element for the one passed as a child element. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | InputColorSwatchBackgroundPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-inputcolor-swatch-background | Class name of the root element |

## Input Color Eye Dropper API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| as | string \| Component | Button | Use to change the HTML tag of root element. |
| asChild | boolean | false | When enabled, it changes the default rendered element for the one passed as a child element. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | InputColorEyeDropperPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-inputcolor-eye-dropper | Class name of the root element |

## Input Color Input API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| as | string \| Component | InputText | Component or HTML tag to render as. Defaults to PrimeVue's  `InputText` . |
| asChild | boolean | false | When enabled, it changes the default rendered element for the one passed as a child element. |
| channel | any | 'hex' | Channel this input drives. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | InputColorInputPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-inputcolor-input | Class name of the root element |

## Input Color Transparency Grid API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| as | string \| Component | DIV | Use to change the HTML tag of root element. |
| asChild | boolean | false | When enabled, it changes the default rendered element for the one passed as a child element. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | InputColorTransparencyGridPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-inputcolor-transparency-grid | Class name of the root element |
