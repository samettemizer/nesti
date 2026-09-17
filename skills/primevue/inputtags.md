# InputTags

InputTags is used to enter multiple tags.

## Basic

InputTags is used to enter multiple tags. Press Enter to add a tag and Backspace to remove the last one.

```vue
<template>
    <div>
        <InputTags v-model="tags" fluid />
    </div>
</template>

<script setup>
import { ref } from 'vue';

const tags = ref(['Vue']);
<\/script>
```

## Delimiter

A custom delimiter like a comma can be used in addition to the Enter key to add tags. Enable addOnPaste to split pasted text using the delimiter.

```vue
<template>
    <div>
        <InputTags v-model="tags" delimiter="," addOnPaste fluid />
    </div>
</template>

<script setup>
import { ref } from 'vue';

const tags = ref([]);
<\/script>
```

## Allow Duplicate

By default, duplicate values are not allowed. Set allowDuplicate to enable adding the same value multiple times.

```vue
<template>
    <div>
        <InputTags v-model="tags" allowDuplicate fluid />
    </div>
</template>

<script setup>
import { ref } from 'vue';

const tags = ref(['a', 'A', 'a']);
<\/script>
```

## Max

The maximum number of tags is limited using the max property.

```vue
<template>
    <div>
        <InputTags v-model="tags" :max="5" fluid />
    </div>
</template>

<script setup>
import { ref } from 'vue';

const tags = ref(['Vue', 'React']);
<\/script>
```

## Template

Custom content can be displayed for each tag using the chip slot.

```vue
<template>
    <div>
        <InputTags v-model="tags" fluid>
            <template #chip="{ value, removeCallback }">
                <Tag rounded>
                    {{ value }}
                    <Times class="cursor-pointer ml-2" style="width: 12px; height: 12px" @click="removeCallback($event)" />
                </Tag>
            </template>
        </InputTags>
    </div>
</template>

<script setup>
import { ref } from 'vue';
import Times from '@primeicons/vue/times';

const tags = ref(['JavaScript', 'TypeScript']);
<\/script>
```

## Typeahead

When typeahead is enabled, a dropdown with suggestions is displayed as the user types. Define a suggestions array along with optionLabel to specify the display field. For grouped suggestions, use optionGroupLabel and optionGroupChildren properties. The complete event is triggered on input change, enabling dynamic filtering and updating of suggestions.

```vue
<template>
    <div class="flex justify-center">
        <InputTags
            v-model="values"
            typeahead
            allowDuplicate
            :suggestions="filteredItems"
            optionLabel="label"
            optionGroupLabel="label"
            optionGroupChildren="items"
            placeholder="Search technologies..."
            class="w-full md:w-56"
            @complete="search"
        />
    </div>
</template>

<script setup>
import { ref } from 'vue';

const values = ref([]);
const items = ref([
    {
        label: 'Frontend',
        items: [{ label: 'React' }, { label: 'Vue' }, { label: 'Angular' }, { label: 'Svelte' }, { label: 'Next.js' }, { label: 'Nuxt' }]
    },
    {
        label: 'Backend',
        items: [{ label: 'Node.js' }, { label: 'Python' }, { label: 'Java' }, { label: 'Go' }, { label: 'Rust' }, { label: 'Ruby' }]
    }
]);
const filteredItems = ref([]);

const search = (event) => {
    const query = event.query.toLowerCase();

    filteredItems.value = items.value
        .map((group) => ({
            ...group,
            items: group.items.filter((item) => item.label.toLowerCase().includes(query))
        }))
        .filter((group) => group.items.length > 0);
};
<\/script>
```

## Events

Use add and remove callbacks to listen for tag changes.

```vue
<template>
    <div>
        <InputTags v-model="tags" placeholder="Add tags and watch the event log..." fluid @add="onAdd" @remove="onRemove" />
        <div v-if="tags.length" class="mt-4 text-sm">
            <span class="text-sm font-medium text-surface-500 dark:text-surface-400 flex items-center gap-2 mb-2">
                <TagIcon size="14" />
                Event Log
            </span>
            <p v-for="(entry, i) of log" :key="\`\${entry}_\${i}\`" class="mb-1!">{{ entry }}</p>
        </div>
    </div>
</template>

<script setup>
import { ref } from 'vue';
import TagIcon from '@primeicons/vue/tag';

const tags = ref(['Vue']);
const log = ref([]);

const onAdd = (event) => {
    log.value = [\`Added: "\${event.value}"\`, ...log.value].slice(0, 5);
};

const onRemove = (event) => {
    log.value = [\`Removed: "\${event.value}" at index \${event.index}\`, ...log.value].slice(0, 5);
};
<\/script>
```

## Float Label

A floating label appears on top of the input field when focused.

```vue
<template>
    <div>
        <FloatLabel>
            <InputTags v-model="tags" inputId="tags" fluid />
            <label for="tags">Technologies</label>
        </FloatLabel>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const tags = ref([]);
<\/script>
```

## Ifta Label

IftaLabel is used to create infield top aligned labels. Visit IftaLabel documentation for more information.

```vue
<template>
    <div>
        <IftaLabel>
            <InputTags v-model="tags" inputId="it_tags" fluid />
            <label for="it_tags">Technologies</label>
        </IftaLabel>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const tags = ref([]);
<\/script>
```

## Filled

Specify the variant property as filled to display the component with a higher visual emphasis than the default outlined style.

```vue
<template>
    <div>
        <InputTags v-model="tags" variant="filled" fluid />
    </div>
</template>

<script setup>
import { ref } from 'vue';

const tags = ref(['Vue']);
<\/script>
```

## Disabled

When disabled is present, the element cannot be edited and focused.

```vue
<template>
    <div>
        <InputTags v-model="tags" disabled fluid />
    </div>
</template>

<script setup>
import { ref } from 'vue';

const tags = ref(['Vue']);
<\/script>
```

## Invalid

The invalid property is used to indicate an invalid state.

```vue
<template>
    <div>
        <InputTags v-model="tags" :invalid="tags.length === 0" fluid />
    </div>
</template>

<script setup>
import { ref } from 'vue';

const tags = ref([]);
<\/script>
```

## Forms

InputTags integrates seamlessly with the PrimeVue Forms library.

```vue
<template>
    <div class="flex justify-center">
        <Form v-slot="$form" :resolver="resolver" :initialValues="initialValues" @submit="onFormSubmit" class="flex justify-center flex-col gap-4 w-full md:w-56">
            <div class="flex flex-col gap-1">
                <InputTags name="tags" placeholder="Add a tag" />
                <Message v-if="$form.tags?.invalid" severity="error" size="small" variant="simple">{{ $form.tags.error?.message }}</Message>
            </div>
            <Button type="submit" severity="secondary">Submit</Button>
        </Form>
    </div>
</template>

<script setup>
import { ref } from "vue";
import { zodResolver } from '@primevue/forms/resolvers/zod';
import { useToast } from "primevue/usetoast";
import { z } from 'zod';

const initialValues = ref({
    tags: []
});
const resolver = ref(zodResolver(
    z.object({
        tags: z.array(z.string()).min(1, { message: 'At least one tag is required.' })
    })
));
const toast = useToast();

const onFormSubmit = ({ valid }) => {
    if (valid) {
        toast.add({ severity: 'success', summary: 'Form is submitted.', life: 3000 });
    }
};
<\/script>
```

## Accessibility

Screen Reader The container of the chip list uses listbox role with aria-orientation set to horizontal. The aria-label and aria-labelledby props can be used to describe the component. When typeahead is enabled, the input element has combobox role in addition to aria-autocomplete , aria-haspopup and aria-expanded attributes. The relation between the input and the popup is created with aria-controls and aria-activedescendant is used to instruct the screen reader which option to read during keyboard navigation within the popup list. A live region with aria-live set to polite announces the number of available results, and the input is linked to it via aria-describedby . Keyboard Support Key Function tab Moves focus to the input element. enter Adds a new tag with the current input value. backspace Removes the last tag when input is empty. left arrow Moves focus to the previous tag when input is empty. right arrow Moves focus to the next tag when focused on a tag. Tag Keyboard Support Key Function backspace Removes the focused tag. delete Removes the focused tag. Popup Keyboard Support (Typeahead) Key Function tab Selects the focused option and closes the popup, then moves focus to next element in page. enter Selects the focused option and closes the popup. escape Closes the popup. down arrow Moves focus to the next option. up arrow Moves focus to the previous option. home Moves focus to the first option. end Moves focus to the last option.

## Input Tags API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| modelValue | string[] | - | Value of the component (array of tag strings). |
| defaultValue | string[] | - | The default value when not controlled by  `modelValue` . |
| name | string | - | The name attribute used in form submissions. |
| typeahead | boolean | false | When enabled, an autocomplete dropdown is shown with the values from the  suggestions  array. |
| suggestions | any[] | - | An array of suggestions to display in the dropdown when  typeahead  is enabled. |
| optionLabel | string \| Function | - | Property name or getter function to use as the label of an option. |
| optionDisabled | string \| Function | - | Property name or getter function to use as the disabled flag of an option. |
| optionGroupLabel | string \| Function | - | Property name or getter function to use as the label of an option group. |
| optionGroupChildren | string \| Function | - | Property name or getter function that refers to the children options of an option group. |
| scrollHeight | string | 14rem | Maximum height of the suggestions overlay. |
| placeholder | string | - | Default placeholder text for the input field. |
| size | any | - | Defines the size of the component. |
| invalid | boolean | false | When present, it specifies that the component should have invalid state style. |
| disabled | boolean | false | When present, it specifies that the component should be disabled. |
| variant | any | null | Specifies the input variant of the component. |
| dataKey | string | - | Property to uniquely identify an option. |
| max | number | - | Maximum number of tags allowed. |
| delimiter | string \| RegExp | - | Character or pattern to use as a delimiter when typing or pasting tags. |
| allowDuplicate | boolean | false | Whether duplicate tags are allowed. |
| addOnBlur | boolean | false | Add the current input value as a tag when the input loses focus. |
| addOnPaste | boolean | false | Add tags from pasted content (split by delimiter when present). |
| addOnTab | boolean | false | Add the current input value as a tag when the Tab key is pressed. |
| minLength | number | 1 | Minimum number of characters required before search is triggered. |
| delay | number | 300 | Delay in milliseconds before sending a search query. |
| appendTo | any | body | A valid query selector or HTMLElement to specify where the overlay attaches. |
| inputId | string | - | Identifier of the underlying input element. |
| inputStyle | object | - | Inline style of the input field. |
| inputClass | string \| object | - | Style class of the input field. |
| inputProps | object | - | Used to pass all properties of the HTMLInputElement to the input element. |
| overlayStyle | object | - | Inline style of the overlay. |
| overlayClass | string \| object | - | Style class of the overlay. |
| autoOptionFocus | boolean | false | Whether to focus on the first visible option when the overlay is shown. |
| focusOnHover | boolean | true | When enabled, the focus is placed on the hovered option. |
| searchMessage | string | - | Text shown in hidden accessible field when filtering returns results. Defaults to PrimeVue locale. |
| emptySearchMessage | string | - | Text shown when filtering returns no results. Defaults to PrimeVue locale. |
| emptyMessage | string | - | Text shown when there are no options to display. Defaults to PrimeVue locale. |
| showEmptyMessage | boolean | true | When enabled, empty message is rendered when there are no options. |
| fluid | boolean | null | Spans 100% width of the container when enabled. |
| ariaLabel | string | - | Defines a string value that labels an interactive element. |
| ariaLabelledby | string | - | Identifier of the element that labels the input. |
| formControl | Record<string, any> | - | Form control object, typically used for handling validation and form state. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | InputTagsPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| item | InputTagsPassThroughOptionType | Used to pass attributes to the chip item element. |
| pcChip | any | Used to pass attributes to the Chip component. |
| pcAutoComplete | any | Used to pass attributes to the AutoComplete component that powers the typeahead suggestion overlay. |
| hiddenInput | InputTagsPassThroughOptionType | Used to pass attributes to the hidden form input's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |
| transition | InputTagsPassThroughTransitionType | Used to control Vue Transition API. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-inputtags | Class name of the root element |
| p-inputtags-item | Class name of the item element |
| p-inputtags-chip-icon | Class name of the chip icon element |
| p-inputtags-autocomplete | Class name applied to the nested AutoComplete instance. |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| inputtags.background | --p-inputtags-background | Background of root |
| inputtags.disabled.background | --p-inputtags-disabled-background | Disabled background of root |
| inputtags.filled.background | --p-inputtags-filled-background | Filled background of root |
| inputtags.filled.hover.background | --p-inputtags-filled-hover-background | Filled hover background of root |
| inputtags.filled.focus.background | --p-inputtags-filled-focus-background | Filled focus background of root |
| inputtags.border.color | --p-inputtags-border-color | Border color of root |
| inputtags.hover.border.color | --p-inputtags-hover-border-color | Hover border color of root |
| inputtags.focus.border.color | --p-inputtags-focus-border-color | Focus border color of root |
| inputtags.invalid.border.color | --p-inputtags-invalid-border-color | Invalid border color of root |
| inputtags.color | --p-inputtags-color | Color of root |
| inputtags.disabled.color | --p-inputtags-disabled-color | Disabled color of root |
| inputtags.shadow | --p-inputtags-shadow | Shadow of root |
| inputtags.padding.x | --p-inputtags-padding-x | Padding x of root |
| inputtags.padding.y | --p-inputtags-padding-y | Padding y of root |
| inputtags.border.radius | --p-inputtags-border-radius | Border radius of root |
| inputtags.focus.ring.width | --p-inputtags-focus-ring-width | Focus ring width of root |
| inputtags.focus.ring.style | --p-inputtags-focus-ring-style | Focus ring style of root |
| inputtags.focus.ring.color | --p-inputtags-focus-ring-color | Focus ring color of root |
| inputtags.focus.ring.offset | --p-inputtags-focus-ring-offset | Focus ring offset of root |
| inputtags.focus.ring.shadow | --p-inputtags-focus-ring-shadow | Focus ring shadow of root |
| inputtags.transition.duration | --p-inputtags-transition-duration | Transition duration of root |
| inputtags.gap | --p-inputtags-gap | Gap of root |
| inputtags.item.border.radius | --p-inputtags-item-border-radius | Border radius of item |
