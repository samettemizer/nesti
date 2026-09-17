# Rating

Rating component is a star based selection input.

## Basic

Two-way value binding is defined using v-model .

```vue
<template>
    <div class="flex justify-center">
        <Rating v-model="value" />
    </div>
</template>

<script setup>
import { ref } from 'vue';

const value = ref(3);
<\/script>
```

## Half Stars

Enable allowHalf property to select half stars.

```vue
<template>
    <div class="flex flex-col gap-6 items-center justify-center">
        <div class="flex flex-col gap-2">
            <Label>Full Star</Label>
            <Rating v-model="value1" />
        </div>
        <div class="flex flex-col gap-2">
            <Label>Half Star</Label>
            <Rating v-model="value2" allowHalf />
        </div>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const value1 = ref(3);
const value2 = ref(3);
<\/script>
```

## Controlled

Rating value can be controlled programmatically.

```vue
<template>
    <div class="flex flex-col items-center justify-center gap-6">
        <Rating v-model="value" allowHalf />
        <div class="flex items-center gap-2">
            <Button @click="value = 2.5" severity="secondary" variant="outlined" size="small">2.5 Star</Button>
            <Button @click="value = 3" severity="secondary" variant="outlined" size="small">3 Star</Button>
            <Button @click="value = 3.5" severity="secondary" variant="outlined" size="small">3.5 Star</Button>
        </div>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const value = ref(4);
<\/script>
```

## Number of Stars

Number of stars to display is defined with stars property.

```vue
<template>
    <div class="flex justify-center">
        <Rating v-model="value" :stars="10" />
    </div>
</template>

<script setup>
import { ref } from 'vue';

const value = ref(5);
<\/script>
```

## Vertical

Rating can be displayed vertically by setting the orientation property to vertical .

```vue
<template>
    <div class="flex justify-center">
        <Rating v-model="value" orientation="vertical" />
    </div>
</template>

<script setup>
import { ref } from 'vue';

const value = ref(3);
<\/script>
```

## Template

Templating allows customizing the content where the icon instance is available as the implicit variable.

```vue
<template>
    <div class="flex flex-col items-center justify-center gap-6">
        <Rating v-model="value1" allowHalf>
            <template #onicon>
                <span class="text-surface-950 dark:text-surface-0 font-medium text-4xl select-none">A</span>
            </template>
            <template #officon>
                <span class="text-surface-300 dark:text-surface-700 font-medium text-4xl select-none">A</span>
            </template>
        </Rating>
        <Rating v-model="value2">
            <template #onicon>
                <span class="size-7">
                    <img src="https://primefaces.org/cdn/primevue/images/rating/custom-onicon.png" class="size-7" />
                </span>
            </template>
            <template #officon>
                <span class="size-7">
                    <img src="https://primefaces.org/cdn/primevue/images/rating/custom-officon.png" class="size-7" />
                </span>
            </template>
        </Rating>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const value1 = ref(3);
const value2 = ref(3);
<\/script>
```

## Emoji

Custom content can be used for rating icons using templates.

```vue
<template>
    <div class="flex justify-center">
        <Rating v-model="value" :stars="5">
            <template #onicon="{ value: index }">
                <span class="text-4xl select-none transition-all">{{ emojis[index - 1] }}</span>
            </template>
            <template #officon="{ value: index }">
                <span class="text-4xl select-none transition-all grayscale">{{ emojis[index - 1] }}</span>
            </template>
        </Rating>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const value = ref(3);
const emojis = ref(['😡', '😕', '😐', '🙂', '😍']);
<\/script>
```

## ReadOnly

When readonly present, value cannot be edited.

```vue
<template>
    <div class="flex justify-center">
        <Rating v-model="value" readonly />
    </div>
</template>

<script setup>
import { ref } from 'vue';

const value = ref(3);
<\/script>
```

## Disabled

When disabled is present, a visual hint is applied to indicate that the Rating cannot be interacted with.

```vue
<template>
    <div class="flex justify-center">
        <Rating v-model="value" disabled />
    </div>
</template>

<script setup>
import { ref } from 'vue';

const value = ref(3);
<\/script>
```

## Forms

Rating integrates seamlessly with the PrimeVue Forms library.

```vue
<template>
    <div class="flex justify-center">
        <Form v-slot="$form" :resolver="resolver" :initialValues="initialValues" @submit="onFormSubmit" class="flex flex-col gap-4 w-40">
            <div class="flex flex-col items-center gap-2">
                <Rating name="rating" />
                <Message v-if="$form.rating?.invalid" severity="error" size="small" variant="simple">{{ $form.rating.error?.message }}</Message>
            </div>
            <Button type="submit" severity="secondary">Submit</Button>
        </Form>
    </div>
</template>

<script setup>
import { ref } from 'vue';
import { zodResolver } from '@primevue/forms/resolvers/zod';
import { useToast } from "primevue/usetoast";
import { z } from 'zod';

const toast = useToast();
const initialValues = ref({
    rating: null
});
const resolver = ref(zodResolver(
    z.object({
        rating: z.union([z.number(), z.literal(null)]).refine((value) => value !== null, { message: 'Rating is required.' })
    })
));

const onFormSubmit = ({ valid }) => {
    if (valid) {
        toast.add({ severity: 'success', summary: 'Form is submitted.', life: 3000 });
    }
};
<\/script>
```

## Accessibility

Screen Reader Rating component internally uses radio buttons that are only visible to screen readers. The value to read for item is retrieved from the locale API via star and stars of the aria property. Keyboard Support Keyboard interaction is derived from the native browser handling of radio buttons in a group. Key Function tab Moves focus to the star representing the value, if there is none then first star receives the focus. left arrow up arrow Moves focus to the previous star, if there is none then last radio button receives the focus. right arrow down arrow Moves focus to the next star, if there is none then first star receives the focus. space If the focused star does not represent the value, changes the value to the star value.

## Rating API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| modelValue | null \| number | - | Value of the rating. |
| defaultValue | null \| number | - | The default value for the input when not controlled by  `modelValue` . |
| name | string | - | Name of the element. |
| disabled | boolean | false | When present, it specifies that the element should be disabled. |
| readonly | boolean | false | When present, it specifies that component is read-only. |
| stars | number | 5 | Number of stars. |
| allowHalf | boolean | false | When enabled, allows half-value selection (e.g. 1.5, 2.5). Each star renders an additional sr-only radio input for the half value. |
| orientation | "horizontal" \| "vertical" | 'horizontal' | Layout orientation of the stars. |
| onIcon | string | - | Icon for the on state. |
| offIcon | string | - | Icon for the off state. |
| formControl | Record<string, any> | - | Form control object, typically used for handling validation and form state. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | RatingPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| option | RatingPassThroughOptionType | Used to pass attributes to the option's DOM element. |
| onIcon | RatingPassThroughOptionType | Used to pass attributes to the on icon's DOM element. |
| offIcon | RatingPassThroughOptionType | Used to pass attributes to the off icon's DOM element. |
| halfInput | RatingPassThroughOptionType | Used to pass attributes to the half-value hidden radio input element (only rendered when  `allowHalf`  is true). |
| fullInput | RatingPassThroughOptionType | Used to pass attributes to the full-value hidden radio input element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-rating | Class name of the root element |
| p-rating-option | Class name of the option element |
| p-rating-on-icon | Class name of the on icon element |
| p-rating-off-icon | Class name of the off icon element |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| rating.gap | --p-rating-gap | Gap of root |
| rating.transition.duration | --p-rating-transition-duration | Transition duration of root |
| rating.focus.ring.width | --p-rating-focus-ring-width | Focus ring width of root |
| rating.focus.ring.style | --p-rating-focus-ring-style | Focus ring style of root |
| rating.focus.ring.color | --p-rating-focus-ring-color | Focus ring color of root |
| rating.focus.ring.offset | --p-rating-focus-ring-offset | Focus ring offset of root |
| rating.focus.ring.shadow | --p-rating-focus-ring-shadow | Focus ring shadow of root |
| rating.icon.size | --p-rating-icon-size | Size of icon |
| rating.icon.color | --p-rating-icon-color | Color of icon |
| rating.icon.hover.color | --p-rating-icon-hover-color | Hover color of icon |
| rating.icon.active.color | --p-rating-icon-active-color | Active color of icon |
