# InputGroup

Text, icon, buttons and other content can be grouped next to an input.

## Basic

Combines an input with addons such as buttons or text labels.

```vue
<template>
    <div class="space-y-4 max-w-xs mx-auto">
        <InputGroup>
            <InputGroupAddon>
                <User />
            </InputGroupAddon>
            <InputText v-model="text1" placeholder="Username" />
        </InputGroup>

        <InputGroup>
            <InputGroupAddon>https://</InputGroupAddon>
            <InputText v-model="text2" placeholder="website" />
            <InputGroupAddon>.com</InputGroupAddon>
        </InputGroup>
    </div>
</template>

<script setup>
import { ref } from 'vue';
import User from '@primeicons/vue/user';

const text1 = ref(null);
const text2 = ref(null);
<\/script>
```

## Multiple

A group is created by wrapping the input and add-ons with the InputGroup component. Each add-on element is defined as a child of InputGroupAddon component. Multiple add-ons can be placed inside the same group.

```vue
<template>
    <div class="max-w-sm mx-auto">
        <InputGroup>
            <InputGroupAddon>
                <Clock />
            </InputGroupAddon>
            <InputGroupAddon>
                <StarFill />
            </InputGroupAddon>
            <InputNumber v-model="value" placeholder="Price" />
            <InputGroupAddon>$</InputGroupAddon>
            <InputGroupAddon>.00</InputGroupAddon>
        </InputGroup>
    </div>
</template>

<script setup>
import { ref } from 'vue';
import Clock from '@primeicons/vue/clock';
import StarFill from '@primeicons/vue/star-fill';

const value = ref(null);
<\/script>
```

## Button

Buttons can be placed at either side of an input element.

```vue
<template>
    <div class="space-y-4 max-w-xs mx-auto">
        <InputGroup>
            <Button>Search</Button>
            <InputText placeholder="Keyword" />
            <InputGroupAddon class="text-xs">8 results</InputGroupAddon>
        </InputGroup>

        <InputGroup>
            <InputText placeholder="Keyword" />
            <InputGroupAddon>
                <Button severity="secondary" variant="text" iconOnly>
                    <Search />
                </Button>
            </InputGroupAddon>
        </InputGroup>

        <InputGroup>
            <InputGroupAddon>
                <Button severity="secondary" iconOnly>
                    <Check />
                </Button>
            </InputGroupAddon>
            <InputText placeholder="Vote" />
            <InputGroupAddon>
                <Button severity="secondary" iconOnly>
                    <Times />
                </Button>
            </InputGroupAddon>
        </InputGroup>
    </div>
</template>

<script setup>
import Check from '@primeicons/vue/check';
import Search from '@primeicons/vue/search';
import Times from '@primeicons/vue/times';
<\/script>
```

## Checkbox & Radio

Checkbox and RadioButton components can be combined with an input element under the same group.

```vue
<template>
    <div class="space-y-4 max-w-xs mx-auto">
        <InputGroup>
            <InputText type="text" placeholder="Price" />
            <InputGroupAddon>
                <RadioButton v-model="radioValue1" name="rb1" value="rb1" />
            </InputGroupAddon>
        </InputGroup>

        <InputGroup>
            <InputGroupAddon>
                <Checkbox v-model="checked1" :binary="true" />
            </InputGroupAddon>
            <InputText type="text" placeholder="Username" />
        </InputGroup>

        <InputGroup>
            <InputGroupAddon>
                <Checkbox v-model="checked2" :binary="true" />
            </InputGroupAddon>
            <InputText type="text" placeholder="Website" />
            <InputGroupAddon>
                <RadioButton v-model="category" name="rb2" value="rb2" />
            </InputGroupAddon>
        </InputGroup>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const radioValue1 = ref(false);
const checked1 = ref(false);
const checked2 = ref(false);
const category = ref(null);
<\/script>
```

## Select

A Select component can be used within an InputGroup alongside other add-ons and inputs.

```vue
<template>
    <div class="space-y-4 max-w-md mx-auto">
        <InputGroup>
            <InputGroupAddon>
                <MapMarker />
            </InputGroupAddon>
            <Select v-model="city1" :options="cities" optionLabel="label" optionValue="value" placeholder="Select a City" class="flex-1" />
        </InputGroup>

        <InputGroup>
            <InputGroupAddon>www</InputGroupAddon>
            <InputText v-model="website" placeholder="Website" class="border-r-0!" />
            <Select v-model="city2" :options="cities" optionLabel="label" optionValue="value" placeholder="Select a City" class="flex-1" />
        </InputGroup>
    </div>
</template>

<script setup>
import { ref } from 'vue';
import MapMarker from '@primeicons/vue/map-marker';

const city1 = ref(null);
const city2 = ref(null);
const website = ref(null);
const cities = ref([
    { label: 'New York', value: 'ny' },
    { label: 'Rome', value: 'rm' },
    { label: 'London', value: 'ldn' },
    { label: 'Istanbul', value: 'ist' },
    { label: 'Paris', value: 'prs' }
]);
<\/script>
```

## Float Label

FloatLabel visually integrates a label with its form element. Visit FloatLabel documentation for more information.

```vue
<template>
    <div class="space-y-4 max-w-xs mx-auto">
        <InputGroup>
            <InputGroupAddon>
                <User />
            </InputGroupAddon>
            <FloatLabel>
                <InputText id="over_label" v-model="value1" />
                <label for="over_label">Over Label</label>
            </FloatLabel>
        </InputGroup>

        <InputGroup>
            <InputGroupAddon>$</InputGroupAddon>
            <FloatLabel variant="in">
                <InputText id="in_label" v-model="value2" />
                <label for="in_label">In Label</label>
            </FloatLabel>
            <InputGroupAddon>.00</InputGroupAddon>
        </InputGroup>

        <InputGroup>
            <InputGroupAddon>www</InputGroupAddon>
            <FloatLabel variant="on">
                <InputText id="on_label" v-model="value3" />
                <label for="on_label">On Label</label>
            </FloatLabel>
        </InputGroup>
    </div>
</template>

<script setup>
import { ref } from 'vue';
import User from '@primeicons/vue/user';

const value1 = ref(null);
const value2 = ref(null);
const value3 = ref(null);
<\/script>
```

## Ifta Label

IftaLabel is used to create infield top aligned labels. Visit IftaLabel documentation for more information.

```vue
<template>
    <div class="max-w-xs mx-auto">
        <InputGroup>
            <InputGroupAddon>
                <User />
            </InputGroupAddon>
            <IftaLabel>
                <InputText id="name" v-model="value" />
                <label for="name">Name</label>
            </IftaLabel>
        </InputGroup>
    </div>
</template>

<script setup>
import { ref } from 'vue';
import User from '@primeicons/vue/user';

const value = ref('Amy');
<\/script>
```

## Accessibility

Screen Reader InputGroup and InputGroupAddon does not require any roles and attributes. Keyboard Support Component does not include any interactive elements.

## Input Group API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Slots

| Name |Parameters |Description |
| --- | --- | --- |
| [key: string] | Function |  |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | InputGroupPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-inputgroup | Class name of the root element |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| inputgroup.addon.background | --p-inputgroup-addon-background | Background of addon |
| inputgroup.addon.border.color | --p-inputgroup-addon-border-color | Border color of addon |
| inputgroup.addon.color | --p-inputgroup-addon-color | Color of addon |
| inputgroup.addon.border.radius | --p-inputgroup-addon-border-radius | Border radius of addon |
| inputgroup.addon.padding | --p-inputgroup-addon-padding | Padding of addon |
| inputgroup.addon.min.width | --p-inputgroup-addon-min-width | Min width of addon |
| inputgroup.addon.font.weight | --p-inputgroup-addon-font-weight | Font weight of addon |
| inputgroup.addon.font.size | --p-inputgroup-addon-font-size | Font size of addon |

## Input Group Addon API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Slots

| Name |Parameters |Description |
| --- | --- | --- |
| [key: string] | Function |  |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | InputGroupAddonPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-inputgroupaddon | Class name of the root element |
