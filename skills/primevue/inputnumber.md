# InputNumber

InputNumber is an input component to provide numerical input.

## Basic

InputNumber is used with the v-model property for two-way value binding.

```vue
<template>
    <div class="flex items-center justify-center">
        <InputNumber v-model="value" />
    </div>
</template>

<script setup>
import { ref } from 'vue';

const value = ref(42723);
<\/script>
```

## Numerals

InputNumber supports decimal numbers with precision control.

```vue
<template>
    <Fluid class="flex flex-wrap gap-4">
        <div class="flex-auto">
            <Label class="font-bold! mb-2 block" for="integeronly">Integer Only</Label>
            <InputNumber v-model="value1" inputId="integeronly" />
        </div>
        <div class="flex-auto">
            <Label class="font-bold! mb-2 block" for="withoutgrouping">Without Grouping</Label>
            <InputNumber v-model="value2" mode="decimal" inputId="withoutgrouping" :useGrouping="false" />
        </div>
        <div class="flex-auto">
            <Label class="font-bold! mb-2 block" for="minmaxfraction">Min-Max Fraction Digits</Label>
            <InputNumber v-model="value3" inputId="minmaxfraction" mode="decimal" :minFractionDigits="2" :maxFractionDigits="5" />
        </div>
        <div class="flex-auto">
            <Label class="font-bold! mb-2 block" for="minmax">Min-Max Boundaries</Label>
            <InputNumber v-model="value4" inputId="minmax" mode="decimal" :min="0" :max="100" />
        </div>
    </Fluid>
</template>

<script setup>
import { ref } from 'vue';

const value1 = ref(42723);
const value2 = ref(58151);
const value3 = ref(2351.35);
const value4 = ref(50);
<\/script>
```

## Locale

Localization information such as grouping and decimal symbols are defined with the locale property which defaults to the user locale.

```vue
<template>
    <Fluid class="flex flex-wrap gap-4">
        <div class="flex-auto">
            <Label class="font-bold! block mb-2" for="locale-user">User Locale</Label>
            <InputNumber v-model="value1" inputId="locale-user" :minFractionDigits="2" />
        </div>
        <div class="flex-auto">
            <Label class="font-bold! block mb-2" for="locale-us">United States Locale</Label>
            <InputNumber v-model="value2" inputId="locale-us" mode="decimal" locale="en-US" :minFractionDigits="2" />
        </div>
        <div class="flex-auto">
            <Label class="font-bold! block mb-2" for="locale-german">German Locale</Label>
            <InputNumber v-model="value3" inputId="locale-german" mode="decimal" locale="de-DE" :minFractionDigits="2" />
        </div>
        <div class="flex-auto">
            <Label class="font-bold! block mb-2" for="locale-indian">Indian Locale</Label>
            <InputNumber v-model="value4" inputId="locale-indian" mode="decimal" locale="en-IN" :minFractionDigits="2" />
        </div>
    </Fluid>
</template>

<script setup>
import { ref } from 'vue';

const value1 = ref(151351);
const value2 = ref(115744);
const value3 = ref(635524);
const value4 = ref(732762);
<\/script>
```

## Currency

Monetary values are enabled by setting mode property as currency . In this setting, currency property also needs to be defined using ISO 4217 standard such as "USD" for the US dollar.

```vue
<template>
    <Fluid class="flex flex-wrap gap-4">
        <div class="flex-auto">
            <Label class="font-bold! block mb-2" for="currency-us">United States</Label>
            <InputNumber v-model="value1" inputId="currency-us" mode="currency" currency="USD" locale="en-US" />
        </div>
        <div class="flex-auto">
            <Label class="font-bold! block mb-2" for="currency-germany">Germany</Label>
            <InputNumber v-model="value2" mode="currency" inputId="currency-germany" currency="EUR" locale="de-DE" />
        </div>
        <div class="flex-auto">
            <Label class="font-bold! block mb-2" for="currency-india">India</Label>
            <InputNumber v-model="value3" mode="currency" inputId="currency-india" currency="INR" currencyDisplay="code" locale="en-IN" />
        </div>
        <div class="flex-auto">
            <Label class="font-bold! block mb-2" for="currency-japan">Japan</Label>
            <InputNumber v-model="value4" mode="currency" inputId="currency-japan" currency="JPY" locale="jp-JP" />
        </div>
    </Fluid>
</template>

<script setup>
import { ref } from 'vue';

const value1 = ref(1500);
const value2 = ref(2500);
const value3 = ref(4250);
const value4 = ref(5002);
<\/script>
```

## Prefix & Suffix

Custom texts e.g. units can be placed before or after the input section with the prefix and suffix properties.

```vue
<template>
    <Fluid class="flex flex-wrap gap-4">
        <div class="flex-auto">
            <Label class="font-bold! block mb-2" for="mile">Mile</Label>
            <InputNumber v-model="value1" inputId="mile" suffix=" mi" />
        </div>
        <div class="flex-auto">
            <Label class="font-bold! block mb-2" for="percent">Percent</Label>
            <InputNumber v-model="value2" inputId="percent" prefix="%" />
        </div>
        <div class="flex-auto">
            <Label class="font-bold! block mb-2" for="expiry">Expiry</Label>
            <InputNumber v-model="value3" inputId="expiry" prefix="Expires in " suffix=" days" />
        </div>
        <div class="flex-auto">
            <Label class="font-bold! block mb-2" for="temperature">Temperature</Label>
            <InputNumber v-model="value4" prefix="↑ " inputId="temperature" suffix="℃" :min="0" :max="40" />
        </div>
    </Fluid>
</template>

<script setup>
import { ref } from 'vue';

const value1 = ref(20);
const value2 = ref(50);
const value3 = ref(10);
const value4 = ref(20);
<\/script>
```

## Buttons

Spinner buttons are enabled using the showButtons property and layout is defined with the buttonLayout .

```vue
<template>
    <Fluid class="flex flex-wrap gap-4">
        <div class="flex-auto">
            <Label class="font-bold! mb-2 block" for="stacked">Stacked</Label>
            <InputNumber v-model="value1" showButtons inputId="stacked" mode="currency" currency="USD" />
        </div>
        <div class="flex-auto">
            <Label class="font-bold! mb-2 block" for="minmax-buttons">Min-Max Boundaries</Label>
            <InputNumber v-model="value2" mode="decimal" showButtons inputId="minmax-buttons" :min="0" :max="100" />
        </div>
        <div class="flex-auto">
            <Label class="font-bold! mb-2 block" for="horizontal">Horizontal with Step</Label>
            <InputNumber v-model="value3" showButtons buttonLayout="horizontal" inputId="horizontal" :step="0.25" mode="currency" currency="EUR">
                <template #incrementicon>
                    <Plus />
                </template>
                <template #decrementicon>
                    <Minus />
                </template>
            </InputNumber>
        </div>
    </Fluid>
</template>

<script setup>
import { ref } from 'vue';

const value1 = ref(20);
const value2 = ref(10.5);
const value3 = ref(25);
<\/script>
```

## Vertical

Buttons can also placed vertically by setting buttonLayout as vertical .

```vue
<template>
    <div class="flex justify-center">
        <InputNumber v-model="value" showButtons buttonLayout="vertical" inputId="vertical" :inputStyle="{ width: '3rem' }">
            <template #incrementicon>
                <Plus />
            </template>
            <template #decrementicon>
                <Minus />
            </template>
        </InputNumber>
    </div>
</template>

<script setup>
import Minus from '@primeicons/vue/minus';
import Plus from '@primeicons/vue/plus';
import { ref } from 'vue';

const value = ref(50);
<\/script>
```

## Float Label

A floating label appears on top of the input field when focused. Visit FloatLabel documentation for more information.

```vue
<template>
    <div class="flex flex-wrap justify-center items-end gap-4">
        <FloatLabel>
            <InputNumber v-model="value1" inputId="over_label" mode="currency" currency="USD" locale="en-US" />
            <label for="over_label">Over Label</label>
        </FloatLabel>

        <FloatLabel variant="in">
            <InputNumber v-model="value2" inputId="in_label" mode="currency" currency="USD" locale="en-US" variant="filled" />
            <label for="in_label">In Label</label>
        </FloatLabel>

        <FloatLabel variant="on">
            <InputNumber v-model="value3" inputId="on_label" mode="currency" currency="USD" locale="en-US" />
            <label for="on_label">On Label</label>
        </FloatLabel>
    </div>
</template>

<script setup>
import { ref } from "vue";

const value1 = ref(null);
const value2 = ref(null);
const value3 = ref(null);
<\/script>
```

## Ifta Label

IftaLabel is used to create infield top aligned labels. Visit IftaLabel documentation for more information.

```vue
<template>
    <div class="flex justify-center">
        <IftaLabel>
            <InputNumber v-model="value" inputId="price_input" mode="currency" currency="USD" locale="en-US" variant="filled" />
            <label for="price_input">Price</label>
        </IftaLabel>
    </div>
</template>

<script setup>
import { ref } from "vue";

const value = ref(1);
<\/script>
```

## Clear Icon

When showClear is enabled, a clear icon is displayed to clear the value.

```vue
<template>
    <div class="flex justify-center">
        <InputNumber v-model="value" inputId="price_input" mode="currency" currency="USD" locale="en-US" showClear inputClass="w-56" />
    </div>
</template>

<script setup>
import { ref } from 'vue';

const value = ref(null);
<\/script>
```

## Sizes

InputNumber provides small and large sizes as alternatives to the base.

```vue
<template>
    <div class="flex flex-col items-center gap-4">
        <InputNumber v-model="value1" size="small" placeholder="Small" mode="currency" currency="USD" locale="en-US" />
        <InputNumber v-model="value2" placeholder="Normal" mode="currency" currency="USD" locale="en-US" />
        <InputNumber v-model="value3" size="large" placeholder="Large" mode="currency" currency="USD" locale="en-US" />
    </div>
</template>

<script setup>
import { ref } from 'vue';

const value1 = ref(null);
const value2 = ref(null);
const value3 = ref(null);
<\/script>
```

## Fluid

The fluid prop makes the component take up the full width of its container when set to true.

```vue
<template>
    <InputNumber v-model="value" inputId="price_input" mode="currency" currency="USD" locale="en-US" fluid />
</template>

<script setup>
import { ref } from 'vue';

const value = ref(null);
<\/script>
```

## Filled

Specify the variant property as filled to display the component with a higher visual emphasis than the default outlined style.

```vue
<template>
    <div class="flex justify-center">
        <InputNumber v-model="value" variant="filled" />
    </div>
</template>

<script setup>
import { ref } from "vue";

const value = ref();
<\/script>
```

## Disabled

When disabled is present, the element cannot be edited and focused.

```vue
<template>
    <div class="flex justify-center">
        <InputNumber v-model="value" inputId="integeronly" disabled prefix="%" />
    </div>
</template>

<script setup>
import { ref } from 'vue';

const value = ref(50);
<\/script>
```

## Invalid

The invalid state is applied using the invalid property to indicate failed validation, which can be integrated with form validation libraries.

```vue
<template>
    <div class="flex flex-wrap justify-center gap-4">
        <InputNumber v-model="value1" :invalid="value1 === null" mode="decimal" :minFractionDigits="2" placeholder="Amount" />
        <InputNumber v-model="value2" :invalid="value2 === null" mode="decimal" :minFractionDigits="2" variant="filled" placeholder="Amount" />
    </div>
</template>

<script setup>
import { ref } from 'vue';

const value1 = ref(null);
const value2 = ref(null);
<\/script>
```

## Forms

InputNumber integrates seamlessly with the PrimeVue Forms library.

```vue
<template>
    <div class="flex justify-center">
        <Form v-slot="$form" :resolver="resolver" :initialValues="initialValues" @submit="onFormSubmit" class="flex flex-col gap-4 w-full sm:w-56">
            <div class="flex flex-col gap-1">
                <InputNumber name="amount" fluid />
                <Message v-if="$form.amount?.invalid" severity="error" size="small" variant="simple">{{ $form.amount.error?.message }}</Message>
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
    amount: null
});
const resolver = ref(zodResolver(
    z.object({
        amount: z.union([z.number().gt(0, { message: 'Must be greater than 0.' }).lt(10, { message: 'Must be less than 10.' }), z.literal(null)]).refine((val) => val !== null, { message: 'Number is required.' })
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

Screen Reader Value to describe the component can either be provided via label tag combined with inputId prop or using aria-labelledby , aria-label , aria-describedby props. The input element uses spinbutton role in addition to the aria-valuemin , aria-valuemax and aria-valuenow attributes. Keyboard Support Key Function tab Moves focus to the input. up arrow Increments the value. down arrow Decrements the value. home Set the minimum value if provided. end Set the maximum value if provided.

```vue
<template>
    <label for="price">Price</label>
    <InputNumber inputId="price" />

    <span id="label_number">Number</span>
    <InputNumber aria-labelledby="label_number" />

    <InputNumber aria-label="Number" />

    <InputNumber aria-describedby="describe" />
    <small id="describe">Information</small>
</template>
```

## Input Number API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| modelValue | any | - | Value of the component. |
| defaultValue | any | - | The default value for the input when not controlled by  `modelValue` . |
| name | string | - | The name attribute for the element, typically used in form submissions. |
| format | boolean | true | Whether to format the value. |
| showButtons | boolean | false | Displays spinner buttons. |
| buttonLayout | any | stacked | Layout of the buttons. |
| incrementButtonClass | string | - | Style class of the increment button. |
| decrementButtonClass | string | - | Style class of the decrement button. |
| incrementIcon | string | - | Style class of the increment icon. |
| decrementIcon | string | - | Style class of the decrement icon. |
| locale | string | - | Locale to be used in formatting. |
| localeMatcher | any | best fit | The locale matching algorithm to use. Possible values are 'lookup' and 'best fit'; the default is 'best fit'. See [Locale Negotation](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Intl#locale_negotiation) for details. |
| mode | any | decimal | Defines the behavior of the component. |
| prefix | string | - | Text to display before the value. |
| suffix | string | - | Text to display after the value. |
| currency | string | - | The currency to use in currency formatting. Possible values are the [ISO 4217 currency codes](https://www.six-group.com/en/products-services/financial-information/data-standards.html#scrollTo=maintenance-agency), such as 'USD' for the US dollar, 'EUR' for the euro, or 'CNY' for the Chinese RMB. There is no default value; if the style is 'currency', the currency property must be provided. |
| currencyDisplay | string | symbol | How to display the currency in currency formatting. Possible values are 'symbol' to use a localized currency symbol such as €, 'code' to use the ISO currency code, 'name' to use a localized currency name such as 'dollar'. |
| useGrouping | boolean | true | Whether to use grouping separators, such as thousands separators or thousand/lakh/crore separators. |
| minFractionDigits | number | - | The minimum number of fraction digits to use. Possible values are from 0 to 20; the default for plain number and percent formatting is 0; the default for currency formatting is the number of minor unit digits provided by the [ISO 4217 currency code](https://www.six-group.com/en/products-services/financial-information/data-standards.html#scrollTo=maintenance-agency) list (2 if the list doesn't provide that information). |
| maxFractionDigits | number | - | The maximum number of fraction digits to use. Possible values are from 0 to 20; the default for plain number formatting is the larger of minimumFractionDigits and 3; the default for currency formatting is the larger of minimumFractionDigits and the number of minor unit digits provided by the [ISO 4217 currency code](https://www.six-group.com/en/products-services/financial-information/data-standards.html#scrollTo=maintenance-agency) list (2 if the list doesn't provide that information). |
| roundingMode | RoundingMode | - | How decimals should be rounded. The default value is  `"halfExpand"` , [further information](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Intl/NumberFormat/NumberFormat#roundingmode). |
| min | number | - | Minimum boundary value. |
| max | number | - | Maximum boundary value. |
| step | number | 1 | Step factor to increment/decrement the value. |
| allowEmpty | boolean | true | Determines whether the input field is empty. |
| highlightOnFocus | boolean | false | Highlights automatically the input value. |
| showClear | boolean | false | When enabled, a clear icon is displayed to clear the value. |
| size | any | - | Defines the size of the component. |
| invalid | boolean | false | When present, it specifies that the component should have invalid state style. |
| disabled | boolean | false | When present, it specifies that the component should be disabled. |
| variant | any | null | Specifies the input variant of the component. |
| readonly | boolean | false | When present, it specifies that an input field is read-only. |
| placeholder | string | - | Placeholder text for the input. |
| fluid | boolean | null | Spans 100% width of the container when enabled. |
| inputId | string | - | Identifier of the focus input to match a label defined for the chips. |
| inputClass | string \| object | - | Style class of the input field. |
| inputStyle | object | - | Inline style of the input field. |
| ariaLabelledby | string | - | Establishes relationships between the component and label(s) where its value should be one or more element IDs. |
| ariaLabel | string | - | Establishes a string value that labels the component. |
| formControl | Record<string, any> | - | Form control object, typically used for handling validation and form state. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | InputNumberPassThroughOptionType<T> | Used to pass attributes to the root's DOM element. |
| pcInputText | any | Used to pass attributes to the InputText component. |
| clearIcon | InputNumberPassThroughOptionType<T> | Used to pass attributes to the label's DOM element. |
| buttonGroup | InputNumberPassThroughOptionType<T> | Used to pass attributes to the button group's DOM element. |
| incrementButton | InputNumberPassThroughOptionType<T> | Used to pass attributes to the increment button's DOM element. |
| incrementIcon | InputNumberPassThroughOptionType<T> | Used to pass attributes to the increment icon's DOM element. |
| decrementButton | InputNumberPassThroughOptionType<T> | Used to pass attributes to the decrement button's DOM element. |
| decrementIcon | InputNumberPassThroughOptionType<T> | Used to pass attributes to the decrement icon's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-inputnumber | Class name of the root element |
| p-inputnumber-input | Class name of the input element |
| p-inputnumber-button-group | Class name of the button group element |
| p-inputnumber-increment-button | Class name of the increment button element |
| p-inputnumber-decrement-button | Class name of the decrement button element |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| inputnumber.transition.duration | --p-inputnumber-transition-duration | Transition duration of root |
| inputnumber.button.width | --p-inputnumber-button-width | Width of button |
| inputnumber.button.border.radius | --p-inputnumber-button-border-radius | Border radius of button |
| inputnumber.button.vertical.padding | --p-inputnumber-button-vertical-padding | Vertical padding of button |
| inputnumber.button.background | --p-inputnumber-button-background | Background of button |
| inputnumber.button.hover.background | --p-inputnumber-button-hover-background | Hover background of button |
| inputnumber.button.active.background | --p-inputnumber-button-active-background | Active background of button |
| inputnumber.button.border.color | --p-inputnumber-button-border-color | Border color of button |
| inputnumber.button.hover.border.color | --p-inputnumber-button-hover-border-color | Hover border color of button |
| inputnumber.button.active.border.color | --p-inputnumber-button-active-border-color | Active border color of button |
| inputnumber.button.color | --p-inputnumber-button-color | Color of button |
| inputnumber.button.hover.color | --p-inputnumber-button-hover-color | Hover color of button |
| inputnumber.button.active.color | --p-inputnumber-button-active-color | Active color of button |
