# AutoComplete

AutoComplete is an input component that provides real-time suggestions when being typed.

## Basic

AutoComplete uses v-model for two-way binding, requires a list of suggestions and a complete method to query for the results. The complete handler gets the query text as event.query property and should update the suggestions with the search results. Use optionLabel to display a property of an object as the suggestion label.

```vue
<template>
    <div class="flex justify-center">
        <AutoComplete v-model="selectedCommand" :suggestions="filteredCommands" @complete="search" optionLabel="label" placeholder="Type a command..." inputClass="w-full md:w-56" scrollHeight="14rem" />
    </div>
</template>

<script setup>
import { ref } from 'vue';

const selectedCommand = ref();
const filteredCommands = ref([]);
const commands = ref([
    { label: 'New File', shortcut: '⌘N' },
    { label: 'Open File', shortcut: '⌘O' },
    { label: 'Save', shortcut: '⌘S' },
    { label: 'Save As', shortcut: '⇧⌘S' },
    { label: 'Find', shortcut: '⌘F' },
    { label: 'Replace', shortcut: '⌘H' },
    { label: 'Go to Line', shortcut: '⌘G' },
    { label: 'Toggle Sidebar', shortcut: '⌘B' },
    { label: 'Split Editor', shortcut: '⌘\\\\' },
    { label: 'Close Tab', shortcut: '⌘W' }
]);

const search = (event) => {
    const query = event.query.toLowerCase();

    filteredCommands.value = query ? commands.value.filter((cmd) => cmd.label.toLowerCase().includes(query)) : [...commands.value];
};
<\/script>
```

## Dropdown

Enabling dropdown property displays a trigger button next to the input field. The dropdownMode property defines the behavior of the button, blank sends an empty query and current sends the current value of the input.

```vue
<template>
    <div class="flex justify-center">
        <AutoComplete v-model="value" dropdown :suggestions="items" @complete="search" inputClass="w-full md:w-56" scrollHeight="14rem" />
    </div>
</template>

<script setup>
import { ref } from 'vue';

const value = ref();
const items = ref([]);

const search = (event) => {
    items.value = event.query ? [...Array(10).keys()].map((item) => event.query + '-' + item) : [...Array(10).keys()].map(String);
};
<\/script>
```

## Custom Option

Customize option content with the option slot.

```vue
<template>
    <div class="flex justify-center">
        <AutoComplete v-model="selectedMember" :suggestions="filteredMembers" @complete="search" optionLabel="name" placeholder="Search team members..." inputClass="w-full md:w-56" scrollHeight="16rem">
            <template #option="slotProps">
                <div class="flex items-center gap-3 py-1">
                    <div class="relative">
                        <Avatar :label="slotProps.option.avatar" shape="circle" class="w-8 h-8" />
                        <span class="absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full border-2 border-surface-0 dark:border-surface-900" :class="slotProps.option.statusClass"></span>
                    </div>
                    <div class="flex flex-col">
                        <span class="font-medium">{{ slotProps.option.name }}</span>
                        <span class="text-xs text-surface-500 dark:text-surface-400">{{ slotProps.option.role }}</span>
                    </div>
                </div>
            </template>
        </AutoComplete>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const selectedMember = ref();
const filteredMembers = ref([]);
const teamMembers = ref([
    { id: 1, name: 'Sarah Chen', role: 'Engineering Lead', avatar: 'SC', status: 'online', statusClass: 'bg-green-400' },
    { id: 2, name: 'Alex Rivera', role: 'Senior Developer', avatar: 'AR', status: 'online', statusClass: 'bg-green-400' },
    { id: 3, name: 'Jordan Kim', role: 'UX Designer', avatar: 'JK', status: 'away', statusClass: 'bg-amber-400' },
    { id: 4, name: 'Taylor Morgan', role: 'Product Manager', avatar: 'TM', status: 'offline', statusClass: 'bg-zinc-400' },
    { id: 5, name: 'Morgan Lee', role: 'DevOps Engineer', avatar: 'ML', status: 'online', statusClass: 'bg-green-400' },
    { id: 6, name: 'Casey Jones', role: 'QA Engineer', avatar: 'CJ', status: 'away', statusClass: 'bg-amber-400' }
]);

const search = (event) => {
    const query = event.query.toLowerCase();

    filteredMembers.value = query ? teamMembers.value.filter((m) => m.name.toLowerCase().includes(query) || m.role.toLowerCase().includes(query)) : [...teamMembers.value];
};
<\/script>
```

## Simple

Options can be grouped by category using the optionGroupLabel and optionGroupChildren properties.

```vue
<template>
    <div class="flex justify-center">
        <AutoComplete
            v-model="selectedTech"
            :suggestions="filteredGroups"
            @complete="search"
            optionLabel="label"
            optionGroupLabel="label"
            optionGroupChildren="items"
            placeholder="Search technologies..."
            inputClass="w-full md:w-56"
            scrollHeight="14rem"
        />
    </div>
</template>

<script setup>
import { ref } from 'vue';

const selectedTech = ref();
const filteredGroups = ref([]);
const techStack = ref([
    {
        label: 'Frontend',
        code: 'FE',
        items: [
            { label: 'React', value: 'react' },
            { label: 'Vue', value: 'vue' },
            { label: 'Angular', value: 'angular' },
            { label: 'Svelte', value: 'svelte' }
        ]
    },
    {
        label: 'Backend',
        code: 'BE',
        items: [
            { label: 'Node.js', value: 'nodejs' },
            { label: 'Python', value: 'python' },
            { label: 'Java', value: 'java' },
            { label: 'Go', value: 'go' }
        ]
    },
    {
        label: 'Database',
        code: 'DB',
        items: [
            { label: 'PostgreSQL', value: 'postgresql' },
            { label: 'MongoDB', value: 'mongodb' },
            { label: 'Redis', value: 'redis' },
            { label: 'MySQL', value: 'mysql' }
        ]
    }
]);

const search = (event) => {
    const query = event.query.toLowerCase();
    const filtered = [];

    for (const category of techStack.value) {
        const filteredItems = query ? category.items.filter((item) => item.label.toLowerCase().includes(query)) : category.items;

        if (filteredItems.length) {
            filtered.push({ ...category, items: filteredItems });
        }
    }

    filteredGroups.value = filtered;
};
<\/script>
```

## Custom

Customize group headers with the optiongroup slot.

```vue
<template>
    <div class="flex justify-center">
        <AutoComplete
            v-model="selectedCity"
            :suggestions="filteredGroups"
            @complete="search"
            optionLabel="label"
            optionGroupLabel="label"
            optionGroupChildren="items"
            placeholder="Search a city..."
            inputClass="w-full md:w-56"
            scrollHeight="18rem"
            :pt="{ optiongroup: 'border-b border-surface' }"
        >
            <template #optiongroup="slotProps">
                <div class="flex items-center gap-2">
                    <span>{{ countryFlags[slotProps.option.value] }}</span>
                    <span>{{ slotProps.option.label }}</span>
                </div>
            </template>
        </AutoComplete>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const selectedCity = ref();
const filteredGroups = ref([]);
const countryFlags = ref({
    de: '🇩🇪',
    us: '🇺🇸',
    jp: '🇯🇵'
});
const groupedCities = ref([
    {
        label: 'Germany',
        value: 'de',
        items: [
            { label: 'Berlin', value: 'Berlin' },
            { label: 'Frankfurt', value: 'Frankfurt' },
            { label: 'Hamburg', value: 'Hamburg' }
        ]
    },
    {
        label: 'USA',
        value: 'us',
        items: [
            { label: 'Chicago', value: 'Chicago' },
            { label: 'Los Angeles', value: 'Los Angeles' },
            { label: 'New York', value: 'New York' }
        ]
    },
    {
        label: 'Japan',
        value: 'jp',
        items: [
            { label: 'Kyoto', value: 'Kyoto' },
            { label: 'Osaka', value: 'Osaka' },
            { label: 'Tokyo', value: 'Tokyo' }
        ]
    }
]);

const search = (event) => {
    const query = event.query.toLowerCase();
    const filtered = [];

    for (const group of groupedCities.value) {
        const filteredItems = query ? group.items.filter((item) => item.label.toLowerCase().includes(query)) : group.items;

        if (filteredItems.length) {
            filtered.push({ ...group, items: filteredItems });
        }
    }

    filteredGroups.value = filtered;
};
<\/script>
```

## Force Selection

ForceSelection mode validates the manual input to check whether it also exists in the suggestions list, if not the input value is cleared to make sure the value passed to the model is always one of the suggestions.

```vue
<template>
    <div class="flex justify-center">
        <AutoComplete v-model="selectedCountry" forceSelection :suggestions="filteredCountries" @complete="search" optionLabel="name" inputClass="w-full md:w-56" scrollHeight="14rem" />
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { CountryService } from '@/service/CountryService';

onMounted(() => {
    CountryService.getCountries().then((data) => (countries.value = data));
});

const countries = ref();
const selectedCountry = ref();
const filteredCountries = ref();

const search = (event) => {
    let query = event.query;
    let filtered = [];

    for (let i = 0; i < countries.value.length; i++) {
        let country = countries.value[i];

        if (country.name.toLowerCase().indexOf(query.toLowerCase()) === 0) {
            filtered.push(country);
        }
    }

    filteredCountries.value = filtered;
};
<\/script>
```

## Float Label

A floating label appears on top of the input field when focused. Visit FloatLabel documentation for more information.

```vue
<template>
    <div class="flex flex-wrap justify-center items-end gap-4">
        <FloatLabel>
            <AutoComplete v-model="value1" inputId="over_label" :suggestions="items" @complete="search" scrollHeight="14rem" />
            <label for="over_label">Over Label</label>
        </FloatLabel>

        <FloatLabel variant="in">
            <AutoComplete v-model="value2" inputId="in_label" :suggestions="items" @complete="search" scrollHeight="14rem" />
            <label for="in_label">In Label</label>
        </FloatLabel>

        <FloatLabel variant="on">
            <AutoComplete v-model="value3" inputId="on_label" :suggestions="items" @complete="search" scrollHeight="14rem" />
            <label for="on_label">On Label</label>
        </FloatLabel>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const value1 = ref();
const value2 = ref();
const value3 = ref();
const items = ref([]);

const search = (event) => {
    items.value = [...Array(10).keys()].map((item) => event.query + '-' + item);
};
<\/script>
```

## Ifta Label

IftaLabel is used to create infield top aligned labels. Visit IftaLabel documentation for more information.

```vue
<template>
    <div class="flex justify-center">
        <IftaLabel>
            <AutoComplete v-model="value" inputId="ac" :suggestions="items" @complete="search" inputClass="w-full md:w-56" scrollHeight="14rem" />
            <label for="ac">Identifier</label>
        </IftaLabel>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const value = ref();
const items = ref([]);

const search = (event) => {
    items.value = [...Array(10).keys()].map((item) => event.query + '-' + item);
};
<\/script>
```

## Clear Icon

When showClear is enabled, a clear icon is displayed to reset the value.

```vue
<template>
    <div class="flex justify-center">
        <AutoComplete v-model="selectedCategory" :suggestions="filteredCategories" @complete="search" optionLabel="label" showClear placeholder="Search categories..." inputClass="w-full md:w-56" scrollHeight="14rem">
            <template #option="slotProps">
                <div class="flex items-center justify-between w-full">
                    <span>{{ slotProps.option.label }}</span>
                    <Tag :value="slotProps.option.count.toString()" severity="secondary" rounded />
                </div>
            </template>
        </AutoComplete>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const selectedCategory = ref();
const filteredCategories = ref([]);
const productCategories = ref([
    { label: 'Electronics', value: 'electronics', count: 1247 },
    { label: 'Clothing', value: 'clothing', count: 856 },
    { label: 'Garden', value: 'home', count: 634 },
    { label: 'Sports', value: 'sports', count: 421 },
    { label: 'Books', value: 'books', count: 2103 },
    { label: 'Toys', value: 'toys', count: 312 }
]);

const search = (event) => {
    const query = event.query.toLowerCase();

    filteredCategories.value = query ? productCategories.value.filter((cat) => cat.label.toLowerCase().includes(query)) : [...productCategories.value];
};
<\/script>
```

## Fluid

The fluid prop makes the component take up the full width of its container when set to true.

```vue
<template>
    <div>
        <AutoComplete v-model="value" :suggestions="items" @complete="search" fluid scrollHeight="14rem" />
    </div>
</template>

<script setup>
import { ref } from 'vue';

const value = ref();
const items = ref([]);

const search = (event) => {
    items.value = [...Array(10).keys()].map((item) => event.query + '-' + item);
};
<\/script>
```

## Loading

Compose a loading indicator alongside the autocomplete input using InputGroup .

```vue
<template>
    <div class="flex justify-center">
        <div class="w-full md:w-56">
            <InputGroup>
                <AutoComplete v-model="value" :suggestions="items" @complete="search" scrollHeight="14rem" />
                <InputGroupAddon>
                    <Spinner class="animate-spin" />
                </InputGroupAddon>
            </InputGroup>
        </div>
    </div>
</template>

<script setup>
import { ref } from 'vue';
import Spinner from '@primeicons/vue/spinner';

const value = ref();
const items = ref([]);

const search = (event) => {
    items.value = [...Array(10).keys()].map((item) => event.query + '-' + item);
};
<\/script>
```

## Sizes

AutoComplete provides small and large sizes as alternatives to the base.

```vue
<template>
    <div class="flex flex-col items-center gap-4">
        <AutoComplete v-model="value1" :suggestions="items" @complete="search" size="small" placeholder="Small" scrollHeight="14rem" />
        <AutoComplete v-model="value2" :suggestions="items" @complete="search" placeholder="Normal" scrollHeight="14rem" />
        <AutoComplete v-model="value3" :suggestions="items" @complete="search" size="large" placeholder="Large" scrollHeight="14rem" />
    </div>
</template>

<script setup>
import { ref } from 'vue';

const value1 = ref();
const value2 = ref();
const value3 = ref();
const items = ref([]);

const search = (event) => {
    items.value = [...Array(10).keys()].map((item) => event.query + '-' + item);
};
<\/script>
```

## Filled

Specify the variant property as filled to display the component with a higher visual emphasis than the default outlined style.

```vue
<template>
    <div class="flex justify-center">
        <AutoComplete v-model="value" :suggestions="items" @complete="search" variant="filled" inputClass="w-full md:w-56" scrollHeight="14rem" />
    </div>
</template>

<script setup>
import { ref } from 'vue';

const value = ref();
const items = ref([]);

const search = (event) => {
    items.value = [...Array(10).keys()].map((item) => event.query + '-' + item);
};
<\/script>
```

## Disabled

When disabled is present, the element cannot be edited and focused.

```vue
<template>
    <div class="flex justify-center">
        <AutoComplete v-model="value" :suggestions="items" @complete="search" disabled placeholder="Disabled" inputClass="w-full md:w-56" scrollHeight="14rem" />
    </div>
</template>

<script setup>
import { ref } from 'vue';

const value = ref();
const items = ref([]);

const search = (event) => {
    items.value = [...Array(10).keys()].map((item) => event.query + '-' + item);
};
<\/script>
```

## Invalid

The invalid state is applied using the invalid property to indicate failed validation, which can be integrated with form validation libraries.

```vue
<template>
    <div class="flex flex-wrap justify-center gap-4">
        <AutoComplete v-model="value1" :suggestions="items" @complete="search" :invalid="!value1" placeholder="Search" inputClass="w-full md:w-56" scrollHeight="14rem" />
        <AutoComplete v-model="value2" :suggestions="items" @complete="search" :invalid="!value2" variant="filled" placeholder="Search" inputClass="w-full md:w-56" scrollHeight="14rem" />
    </div>
</template>

<script setup>
import { ref } from 'vue';

const value1 = ref();
const value2 = ref();
const items = ref([]);

const search = (event) => {
    items.value = [...Array(10).keys()].map((item) => event.query + '-' + item);
};
<\/script>
```

## Focus Behavior

Customize keyboard and mouse focus behavior with autoOptionFocus , selectOnFocus , and focusOnHover properties.

```vue
<template>
    <div class="space-y-4">
        <div class="flex flex-wrap gap-2 justify-center">
            <Button size="small" :severity="autoOptionFocus ? 'primary' : 'secondary'" @click="autoOptionFocus = !autoOptionFocus">{{ \`autoOptionFocus: \${autoOptionFocus}\` }}</Button>
            <Button size="small" :severity="selectOnFocus ? 'primary' : 'secondary'" @click="selectOnFocus = !selectOnFocus">{{ \`selectOnFocus: \${selectOnFocus}\` }}</Button>
            <Button size="small" :severity="focusOnHover ? 'primary' : 'secondary'" @click="focusOnHover = !focusOnHover">{{ \`focusOnHover: \${focusOnHover}\` }}</Button>
        </div>
        <div class="flex justify-center">
            <AutoComplete
                v-model="value"
                :suggestions="items"
                @complete="search"
                :autoOptionFocus="autoOptionFocus"
                :selectOnFocus="selectOnFocus"
                :focusOnHover="focusOnHover"
                placeholder="Search a city..."
                inputClass="w-full md:w-56"
                scrollHeight="14rem"
            />
        </div>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const value = ref();
const items = ref([]);
const autoOptionFocus = ref(true);
const selectOnFocus = ref(false);
const focusOnHover = ref(true);

const search = (event) => {
    items.value = [...Array(10).keys()].map((item) => event.query + '-' + item);
};
<\/script>
```

## Objects

AutoComplete can also work with objects using the optionLabel property that defines the label to display as a suggestion. The value passed to the model would still be the object instance of a suggestion. Here is an example with a Country object that has name and code fields such as &#123;name: "United States", code:"USA"&#125; .

```vue
<template>
    <div class="flex justify-center">
        <AutoComplete v-model="selectedCountry" :suggestions="filteredCountries" @complete="search" optionLabel="name" inputClass="w-full md:w-56" scrollHeight="14rem" placeholder="Search a country..." />
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { CountryService } from '@/service/CountryService';

onMounted(() => {
    CountryService.getCountries().then((data) => (countries.value = data));
});

const countries = ref();
const selectedCountry = ref();
const filteredCountries = ref();

const search = (event) => {
    let query = event.query;
    let filtered = [];

    for (let i = 0; i < countries.value.length; i++) {
        let country = countries.value[i];

        if (country.name.toLowerCase().indexOf(query.toLowerCase()) === 0) {
            filtered.push(country);
        }
    }

    filteredCountries.value = filtered;
};
<\/script>
```

## Template

AutoComplete offers multiple slots for customization through templating.

```vue
<template>
    <div class="flex justify-center">
        <AutoComplete v-model="selectedCountry" :suggestions="filteredCountries" @complete="search" optionLabel="name" inputClass="w-full md:w-56" scrollHeight="14rem">
            <template #option="slotProps">
                <div class="flex items-center gap-2">
                    <img :alt="slotProps.option.name" src="https://primefaces.org/cdn/primevue/images/flag/flag_placeholder.png" :class="\`flag flag-\${slotProps.option.code.toLowerCase()}\`" style="width: 18px" />
                    <div>{{ slotProps.option.name }}</div>
                </div>
            </template>
            <template #header>
                <div class="font-medium px-3 py-2">Available Countries</div>
            </template>
            <template #footer>
                <div class="px-3 py-3">
                    <Button fluid severity="secondary" text size="small">
                        <Plus />
                        Add New
                    </Button>
                </div>
            </template>
        </AutoComplete>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { CountryService } from '@/service/CountryService';
import Plus from '@primeicons/vue/plus';

onMounted(() => {
    CountryService.getCountries().then((data) => (countries.value = data));
});

const countries = ref();
const selectedCountry = ref();
const filteredCountries = ref();

const search = (event) => {
    let query = event.query;
    let filtered = [];

    for (let i = 0; i < countries.value.length; i++) {
        let country = countries.value[i];

        if (country.name.toLowerCase().indexOf(query.toLowerCase()) === 0) {
            filtered.push(country);
        }
    }

    filteredCountries.value = filtered;
};
<\/script>
```

## Virtual Scroll

Virtual scrolling is an efficient way of rendering the options by displaying a small subset of data in the viewport at any time. When dealing with huge number of options, it is suggested to enable virtual scrolling to avoid performance issues. Configuration of the scroll behavior is defined with virtualScrollerOptions that requires itemSize as the mandatory value to set the height of an item. Visit VirtualScroller documentation for more information about the configuration API.

```vue
<template>
    <div class="flex justify-center">
        <AutoComplete v-model="selectedItem" :suggestions="filteredItems" @complete="search" :virtualScrollerOptions="{ itemSize: 34 }" optionLabel="label" dropdown />
    </div>
</template>

<script setup>
import { ref } from 'vue';

const items = ref(Array.from({ length: 10000 }, (_, i) => ({ label: 'Item ' + i, value: 'Item ' + i })));
const selectedItem = ref();
const filteredItems = ref();

const search = (event) => {
    //in a real application, make a request to a remote url with the query and return filtered results, for demo we filter at client side
    let query = event.query;
    let filtered = [];

    for (let i = 0; i < items.value.length; i++) {
        let item = items.value[i];

        if (item.label.toLowerCase().indexOf(query.toLowerCase()) === 0) {
            filtered.push(item);
        }
    }

    filteredItems.value = filtered;
};
<\/script>
```

## Forms

AutoComplete integrates seamlessly with the PrimeVue Forms library.

```vue
<template>
    <div class="flex justify-center">
        <Form v-slot="$form" :resolver="resolver" :initialValues="initialValues" @submit="onFormSubmit" class="flex justify-center flex-col gap-4 w-full md:w-56">
            <div class="flex flex-col gap-1">
                <AutoComplete name="value" :suggestions="items" @complete="search" fluid />
                <Message v-if="$form.value?.invalid" severity="error" size="small" variant="simple">{{ $form.value.error?.message }}</Message>
            </div>
            <Button type="submit" severity="secondary">Submit</Button>
        </Form>
    </div>
</template>

<script setup>
import { ref } from 'vue';
import { zodResolver } from '@primevue/forms/resolvers/zod';
import { useToast } from 'primevue/usetoast';
import { z } from 'zod';

const toast = useToast();
const items = ref([]);
const initialValues = ref({
    value: ''
});
const resolver = ref(zodResolver(
    z.object({
        value: z.string().min(1, { message: 'Value is required.' })
    })
));

const search = (event) => {
    items.value = [...Array(10).keys()].map((item) => event.query + '-' + item);
};

const onFormSubmit = ({ valid }) => {
    if (valid) {
        toast.add({ severity: 'success', summary: 'Form is submitted.', life: 3000 });
    }
};
<\/script>
```

## Accessibility

Screen Reader Value to describe the component can either be provided via label tag combined with inputId prop or using aria-labelledby , aria-label props. The input element has combobox role in addition to aria-autocomplete , aria-haspopup and aria-expanded attributes. The relation between the input and the popup is created with aria-controls and aria-activedescendant attribute is used to instruct screen reader which option to read during keyboard navigation within the popup list. In multiple mode, chip list uses listbox role whereas each chip has the option role with aria-label set to the label of the chip. The popup list has an id that refers to the aria-controls attribute of the input element and uses listbox as the role. Each list item has option role and an id to match the aria-activedescendant of the input element. Keyboard Support Key Function tab Moves focus to the input element when popup is not visible. If the popup is open and an item is highlighted then popup gets closed, item gets selected and focus moves to the next focusable element. up arrow Highlights the previous item if popup is visible. down arrow Highlights the next item if popup is visible. enter Selects the highlighted item and closes the popup if popup is visible. home Highlights the first item if popup is visible. end Highlights the last item if popup is visible. escape Hides the popup. Chips Input Keyboard Support Key Function backspace Deletes the previous chip if the input field is empty. left arrow Moves focus to the previous chip if available and input field is empty. Chip Keyboard Support Key Function left arrow Moves focus to the previous chip if available. right arrow Moves focus to the next chip, if there is none then input field receives the focus. backspace Deletes the chips and adds focus to the input field.

```vue
<template>
    <label for="ac1">Username</label>
    <AutoComplete inputId="ac1" />

    <span id="ac2">Email</span>
    <AutoComplete aria-labelledby="ac2" />

    <AutoComplete aria-label="City" />
</template>
```

## Auto Complete API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| modelValue | any | - | Value of the component. |
| defaultValue | any | - | The default value for the input when not controlled by  `modelValue` . |
| name | string | - | The name attribute for the element, typically used in form submissions. |
| suggestions | any[] | - | An array of suggestions to display. |
| optionLabel | string \| Function | - | Property name or getter function to use as the label of an option. |
| optionDisabled | string \| Function | - | Property name or getter function to use as the disabled flag of an option, defaults to false when not defined. |
| optionGroupLabel | string \| Function | - | Property name or getter function to use as the label of an option group. |
| optionGroupChildren | string \| Function | - | Property name or getter function that refers to the children options of option group. |
| typeahead | boolean | true | whether typeahead is active or not. |
| scrollHeight | string | 14rem | Maximum height of the suggestions overlay. |
| dropdown | boolean | false | Displays a button next to the input field when enabled. |
| dropdownMode | any | blank | Specifies the behavior dropdown button. Default 'blank' mode sends an empty string and 'current' mode sends the input value. |
| multiple | boolean | false | Specifies if multiple values can be selected. |
| showClear | boolean | false | When enabled, a clear icon is displayed to clear the value. |
| placeholder | string | - | Default text to display when no option is selected. |
| loading | boolean | false | Whether the autocomplete is in loading state. |
| size | any | - | Defines the size of the component. |
| invalid | boolean | false | When present, it specifies that the component should have invalid state style. |
| disabled | boolean | false | When present, it specifies that the component should be disabled. |
| variant | any | null | Specifies the input variant of the component. |
| dataKey | string | - | A property to uniquely identify an option. |
| minLength | number | 1 | Minimum number of characters to initiate a search. |
| delay | number | 300 | Delay between keystrokes to wait before sending a query. |
| appendTo | any | body | A valid query selector or an HTMLElement to specify where the overlay gets attached. Special keywords are 'body' for document body and 'self' for the element itself. |
| forceSelection | boolean | false | When present, autocomplete clears the manual input if it does not match of the suggestions to force only accepting values from the suggestions. |
| completeOnFocus | boolean | false | Whether to run a query when input receives focus. |
| inputId | string | - | Identifier of the underlying input element. |
| inputStyle | object | - | Inline style of the input field. |
| inputClass | string \| object | - | Style class of the input field. |
| inputProps | InputHTMLAttributes | - | Used to pass all properties of the HTMLInputElement to the focusable input element inside the component. |
| panelStyle | object | - | Inline style of the overlay. |
| panelClass | string \| object | - | Style class of the overlay. |
| overlayStyle | object | - | Inline style of the overlay overlay. |
| overlayClass | string \| object | - | Style class of the overlay overlay. |
| dropdownIcon | string | - | Icon to display in the dropdown. |
| dropdownClass | string \| object | - | Style class of the dropdown button. |
| loader | string | - | Icon to display in loading state. |
| chipIcon | string | - | Icon to display in chip remove action. |
| virtualScrollerOptions | any | - | Whether to use the virtualScroller feature. The properties of VirtualScroller component can be used like an object in it. |
| autoOptionFocus | boolean | false | Whether to focus on the first visible or selected element when the overlay is shown. |
| selectOnFocus | boolean | false | When enabled, the focused option is selected. |
| focusOnHover | boolean | true | When enabled, the focus is placed on the hovered option. |
| searchLocale | string | - | Locale to use in searching. The default locale is the host environment's current locale. |
| searchMessage | string | '{0} results are available' | Text to be displayed in hidden accessible field when filtering returns any results. Defaults to value from PrimeVue locale configuration. |
| selectionMessage | string | '{0} items selected' | Text to be displayed in hidden accessible field when options are selected. Defaults to value from PrimeVue locale configuration. |
| emptySelectionMessage | string | No selected item | Text to be displayed in hidden accessible field when any option is not selected. Defaults to value from PrimeVue locale configuration. |
| emptySearchMessage | string | No results found | Text to display when filtering does not return any results. Defaults to value from PrimeVue locale configuration. |
| showEmptyMessage | boolean | true | When enabled, empty search message will be visible. |
| tabindex | string \| number | - | Index of the element in tabbing order. |
| fluid | boolean | null | Spans 100% width of the container when enabled. |
| ariaLabel | string | - | Defines a string value that labels an interactive element. |
| ariaLabelledby | string | - | Identifier of the underlying input element. |
| formControl | Record<string, any> | - | Form control object, typically used for handling validation and form state. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | AutoCompletePassThroughOptionType | Used to pass attributes to the root's DOM element. |
| pcInputText | any | Used to pass attributes to the InputText component. |
| inputMultiple | AutoCompletePassThroughOptionType | Used to pass attributes to the input multiple's DOM element. |
| chipItem | AutoCompletePassThroughOptionType | Used to pass attributes to the chip's DOM element. |
| pcChip | any | Used to pass attributes to the Chip. |
| chipIcon | AutoCompletePassThroughOptionType | Used to pass attributes to the chip icon's DOM element. |
| input | AutoCompletePassThroughOptionType | Used to pass attributes to the input chip's DOM element. |
| inputChip | AutoCompletePassThroughOptionType | Used to pass attributes to the input chip's DOM element. |
| loader | AutoCompletePassThroughOptionType | Used to pass attributes to the loader's DOM element. |
| clearIcon | AutoCompletePassThroughOptionType | Used to pass attributes to the clear icon's DOM element. |
| dropdown | AutoCompletePassThroughOptionType | Used to pass attributes to the dropdown's DOM element. |
| dropdownIcon | AutoCompletePassThroughOptionType | Used to pass attributes to the dropdown icon's DOM element. |
| overlay | AutoCompletePassThroughOptionType | Used to pass attributes to the overlay's DOM element. |
| virtualScroller | any | Used to pass attributes to the VirtualScroller component. |
| listContainer | AutoCompletePassThroughOptionType | Used to pass attributes to the list container's DOM element. |
| list | AutoCompletePassThroughOptionType | Used to pass attributes to the list's DOM element. |
| optionGroup | AutoCompletePassThroughOptionType | Used to pass attributes to the option group's DOM element. |
| option | AutoCompletePassThroughOptionType | Used to pass attributes to the option's DOM element. |
| emptyMessage | AutoCompletePassThroughOptionType | Used to pass attributes to the empty message's DOM element. |
| searchResultMessage | AutoCompletePassThroughOptionType | Used to pass attributes to the search result message's DOM element. |
| selectedMessage | AutoCompletePassThroughOptionType | Used to pass attributes to the selected message's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |
| transition | AutoCompletePassThroughTransitionType | Used to control Vue Transition API. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-autocomplete | Class name of the root element |
| p-autocomplete-input | Class name of the input element |
| p-autocomplete-input-multiple | Class name of the input multiple element |
| p-autocomplete-clear-icon | Class name of the clear icon element |
| p-autocomplete-chip-item | Class name of the chip item element |
| p-autocomplete-chip | Class name of the chip element |
| p-autocomplete-chip-icon | Class name of the chip icon element |
| p-autocomplete-input-chip | Class name of the input chip element |
| p-autocomplete-loader | Class name of the loader element |
| p-autocomplete-dropdown | Class name of the dropdown element |
| p-autocomplete-overlay | Class name of the panel element |
| p-autocomplete-list | Class name of the list element |
| p-autocomplete-list-container | Class name of the list container element |
| p-autocomplete-option-group | Class name of the option group element |
| p-autocomplete-option | Class name of the option element |
| p-autocomplete-empty-message | Class name of the empty message element |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| autocomplete.background | --p-autocomplete-background | Background of root |
| autocomplete.disabled.background | --p-autocomplete-disabled-background | Disabled background of root |
| autocomplete.filled.background | --p-autocomplete-filled-background | Filled background of root |
| autocomplete.filled.hover.background | --p-autocomplete-filled-hover-background | Filled hover background of root |
| autocomplete.filled.focus.background | --p-autocomplete-filled-focus-background | Filled focus background of root |
| autocomplete.border.color | --p-autocomplete-border-color | Border color of root |
| autocomplete.hover.border.color | --p-autocomplete-hover-border-color | Hover border color of root |
| autocomplete.focus.border.color | --p-autocomplete-focus-border-color | Focus border color of root |
| autocomplete.invalid.border.color | --p-autocomplete-invalid-border-color | Invalid border color of root |
| autocomplete.color | --p-autocomplete-color | Color of root |
| autocomplete.disabled.color | --p-autocomplete-disabled-color | Disabled color of root |
| autocomplete.placeholder.color | --p-autocomplete-placeholder-color | Placeholder color of root |
| autocomplete.invalid.placeholder.color | --p-autocomplete-invalid-placeholder-color | Invalid placeholder color of root |
| autocomplete.shadow | --p-autocomplete-shadow | Shadow of root |
| autocomplete.padding.x | --p-autocomplete-padding-x | Padding x of root |
| autocomplete.padding.y | --p-autocomplete-padding-y | Padding y of root |
| autocomplete.border.radius | --p-autocomplete-border-radius | Border radius of root |
| autocomplete.focus.ring.width | --p-autocomplete-focus-ring-width | Focus ring width of root |
| autocomplete.focus.ring.style | --p-autocomplete-focus-ring-style | Focus ring style of root |
| autocomplete.focus.ring.color | --p-autocomplete-focus-ring-color | Focus ring color of root |
| autocomplete.focus.ring.offset | --p-autocomplete-focus-ring-offset | Focus ring offset of root |
| autocomplete.focus.ring.shadow | --p-autocomplete-focus-ring-shadow | Focus ring shadow of root |
| autocomplete.transition.duration | --p-autocomplete-transition-duration | Transition duration of root |
| autocomplete.overlay.background | --p-autocomplete-overlay-background | Background of overlay |
| autocomplete.overlay.border.color | --p-autocomplete-overlay-border-color | Border color of overlay |
| autocomplete.overlay.border.radius | --p-autocomplete-overlay-border-radius | Border radius of overlay |
| autocomplete.overlay.color | --p-autocomplete-overlay-color | Color of overlay |
| autocomplete.overlay.shadow | --p-autocomplete-overlay-shadow | Shadow of overlay |
| autocomplete.list.padding | --p-autocomplete-list-padding | Padding of list |
| autocomplete.list.gap | --p-autocomplete-list-gap | Gap of list |
| autocomplete.option.focus.background | --p-autocomplete-option-focus-background | Focus background of option |
| autocomplete.option.selected.background | --p-autocomplete-option-selected-background | Selected background of option |
| autocomplete.option.selected.focus.background | --p-autocomplete-option-selected-focus-background | Selected focus background of option |
| autocomplete.option.color | --p-autocomplete-option-color | Color of option |
| autocomplete.option.focus.color | --p-autocomplete-option-focus-color | Focus color of option |
| autocomplete.option.selected.color | --p-autocomplete-option-selected-color | Selected color of option |
| autocomplete.option.selected.focus.color | --p-autocomplete-option-selected-focus-color | Selected focus color of option |
| autocomplete.option.padding | --p-autocomplete-option-padding | Padding of option |
| autocomplete.option.border.radius | --p-autocomplete-option-border-radius | Border radius of option |
| autocomplete.option.font.weight | --p-autocomplete-option-font-weight | Font weight of option |
| autocomplete.option.font.size | --p-autocomplete-option-font-size | Font size of option |
| autocomplete.option.group.background | --p-autocomplete-option-group-background | Background of option group |
| autocomplete.option.group.color | --p-autocomplete-option-group-color | Color of option group |
| autocomplete.option.group.font.weight | --p-autocomplete-option-group-font-weight | Font weight of option group |
| autocomplete.option.group.font.size | --p-autocomplete-option-group-font-size | Font size of option group |
| autocomplete.option.group.padding | --p-autocomplete-option-group-padding | Padding of option group |
| autocomplete.dropdown.width | --p-autocomplete-dropdown-width | Width of dropdown |
| autocomplete.dropdown.sm.width | --p-autocomplete-dropdown-sm-width | Sm width of dropdown |
| autocomplete.dropdown.lg.width | --p-autocomplete-dropdown-lg-width | Lg width of dropdown |
| autocomplete.dropdown.border.color | --p-autocomplete-dropdown-border-color | Border color of dropdown |
| autocomplete.dropdown.hover.border.color | --p-autocomplete-dropdown-hover-border-color | Hover border color of dropdown |
| autocomplete.dropdown.active.border.color | --p-autocomplete-dropdown-active-border-color | Active border color of dropdown |
| autocomplete.dropdown.border.radius | --p-autocomplete-dropdown-border-radius | Border radius of dropdown |
| autocomplete.dropdown.focus.ring.width | --p-autocomplete-dropdown-focus-ring-width | Focus ring width of dropdown |
| autocomplete.dropdown.focus.ring.style | --p-autocomplete-dropdown-focus-ring-style | Focus ring style of dropdown |
| autocomplete.dropdown.focus.ring.color | --p-autocomplete-dropdown-focus-ring-color | Focus ring color of dropdown |
| autocomplete.dropdown.focus.ring.offset | --p-autocomplete-dropdown-focus-ring-offset | Focus ring offset of dropdown |
| autocomplete.dropdown.focus.ring.shadow | --p-autocomplete-dropdown-focus-ring-shadow | Focus ring shadow of dropdown |
| autocomplete.dropdown.background | --p-autocomplete-dropdown-background | Background of dropdown |
| autocomplete.dropdown.hover.background | --p-autocomplete-dropdown-hover-background | Hover background of dropdown |
| autocomplete.dropdown.active.background | --p-autocomplete-dropdown-active-background | Active background of dropdown |
| autocomplete.dropdown.color | --p-autocomplete-dropdown-color | Color of dropdown |
| autocomplete.dropdown.hover.color | --p-autocomplete-dropdown-hover-color | Hover color of dropdown |
| autocomplete.dropdown.active.color | --p-autocomplete-dropdown-active-color | Active color of dropdown |
| autocomplete.chip.border.radius | --p-autocomplete-chip-border-radius | Border radius of chip |
| autocomplete.chip.focus.background | --p-autocomplete-chip-focus-background | Focus background of chip |
| autocomplete.chip.focus.color | --p-autocomplete-chip-focus-color | Focus color of chip |
| autocomplete.empty.message.padding | --p-autocomplete-empty-message-padding | Padding of empty message |
