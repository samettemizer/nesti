# Stepper

The Stepper component displays a wizard-like workflow by guiding users through the multi-step progression.

## Horizontal

Stepper consists of a combination of StepList , Step , StepPanels and StepPanel components. The value property is essential for associating Step and StepPanel with each other.

```vue
<template>
    <div class="flex justify-center">
        <Stepper value="1" class="basis-200 min-w-0">
            <StepList>
                <Step value="1">Header I</Step>
                <Step value="2">Header II</Step>
                <Step value="3">Header III</Step>
            </StepList>
            <StepPanels>
                <StepPanel v-slot="{ activateCallback }" value="1">
                    <div class="flex flex-col h-48">
                        <div class="border-2 border-dashed border-surface-200 dark:border-surface-700 rounded-sm bg-surface-50 dark:bg-surface-950 flex-auto flex justify-center items-center font-medium text-sm">Content I</div>
                    </div>
                    <div class="flex pt-5 justify-end">
                        <Button @click="activateCallback('2')">
                            Next
                            <ArrowRight />
                        </Button>
                    </div>
                </StepPanel>
                <StepPanel v-slot="{ activateCallback }" value="2">
                    <div class="flex flex-col h-48">
                        <div class="border-2 border-dashed border-surface-200 dark:border-surface-700 rounded-sm bg-surface-50 dark:bg-surface-950 flex-auto flex justify-center items-center font-medium text-sm">Content II</div>
                    </div>
                    <div class="flex pt-5 justify-between">
                        <Button severity="secondary" @click="activateCallback('1')">
                            <ArrowLeft />
                            Back
                        </Button>
                        <Button @click="activateCallback('3')">
                            Next
                            <ArrowRight />
                        </Button>
                    </div>
                </StepPanel>
                <StepPanel v-slot="{ activateCallback }" value="3">
                    <div class="flex flex-col h-48">
                        <div class="border-2 border-dashed border-surface-200 dark:border-surface-700 rounded-sm bg-surface-50 dark:bg-surface-950 flex-auto flex justify-center items-center font-medium text-sm">Content III</div>
                    </div>
                    <div class="pt-5">
                        <Button severity="secondary" @click="activateCallback('2')">
                            <ArrowLeft />
                            Back
                        </Button>
                    </div>
                </StepPanel>
            </StepPanels>
        </Stepper>
    </div>
</template>

<script setup>
import ArrowLeft from '@primeicons/vue/arrow-left';
import ArrowRight from '@primeicons/vue/arrow-right';
<\/script>
```

## Vertical

Vertical layout requires StepItem as a wrapper of Step and StepPanel components.

```vue
<template>
    <div>
        <Stepper value="1">
            <StepItem value="1">
                <Step>Header I</Step>
                <StepPanel v-slot="{ activateCallback }">
                    <div class="flex flex-col h-48">
                        <div class="border-2 border-dashed border-surface-200 dark:border-surface-700 rounded-sm bg-surface-50 dark:bg-surface-950 flex-auto flex justify-center items-center font-medium text-sm">Content I</div>
                    </div>
                    <div class="py-5">
                        <Button @click="activateCallback('2')">Next</Button>
                    </div>
                </StepPanel>
            </StepItem>
            <StepItem value="2">
                <Step>Header II</Step>
                <StepPanel v-slot="{ activateCallback }">
                    <div class="flex flex-col h-48">
                        <div class="border-2 border-dashed border-surface-200 dark:border-surface-700 rounded-sm bg-surface-50 dark:bg-surface-950 flex-auto flex justify-center items-center font-medium text-sm">Content II</div>
                    </div>
                    <div class="flex py-5 gap-2">
                        <Button severity="secondary" @click="activateCallback('1')">Back</Button>
                        <Button @click="activateCallback('3')">Next</Button>
                    </div>
                </StepPanel>
            </StepItem>
            <StepItem value="3">
                <Step>Header III</Step>
                <StepPanel v-slot="{ activateCallback }">
                    <div class="flex flex-col h-48">
                        <div class="border-2 border-dashed border-surface-200 dark:border-surface-700 rounded-sm bg-surface-50 dark:bg-surface-950 flex-auto flex justify-center items-center font-medium text-sm">Content III</div>
                    </div>
                    <div class="py-5">
                        <Button severity="secondary" @click="activateCallback('2')">Back</Button>
                    </div>
                </StepPanel>
            </StepItem>
        </Stepper>
    </div>
</template>
```

## Linear

When linear property is present, current step must be completed in order to move to the next step.

```vue
<template>
    <div class="flex justify-center">
        <Stepper value="1" linear class="basis-200 min-w-0">
            <StepList>
                <Step value="1">Header I</Step>
                <Step value="2">Header II</Step>
                <Step value="3">Header III</Step>
            </StepList>
            <StepPanels>
                <StepPanel v-slot="{ activateCallback }" value="1">
                    <div class="flex flex-col h-48">
                        <div class="border-2 border-dashed border-surface-200 dark:border-surface-700 rounded-sm bg-surface-50 dark:bg-surface-950 flex-auto flex justify-center items-center font-medium text-sm">Content I</div>
                    </div>
                    <div class="flex pt-5 justify-end">
                        <Button @click="activateCallback('2')">
                            Next
                            <ArrowRight />
                        </Button>
                    </div>
                </StepPanel>
                <StepPanel v-slot="{ activateCallback }" value="2">
                    <div class="flex flex-col h-48">
                        <div class="border-2 border-dashed border-surface-200 dark:border-surface-700 rounded-sm bg-surface-50 dark:bg-surface-950 flex-auto flex justify-center items-center font-medium text-sm">Content II</div>
                    </div>
                    <div class="flex pt-5 justify-between">
                        <Button severity="secondary" @click="activateCallback('1')">
                            <ArrowLeft />
                            Back
                        </Button>
                        <Button @click="activateCallback('3')">
                            Next
                            <ArrowRight />
                        </Button>
                    </div>
                </StepPanel>
                <StepPanel v-slot="{ activateCallback }" value="3">
                    <div class="flex flex-col h-48">
                        <div class="border-2 border-dashed border-surface-200 dark:border-surface-700 rounded-sm bg-surface-50 dark:bg-surface-950 flex-auto flex justify-center items-center font-medium text-sm">Content III</div>
                    </div>
                    <div class="pt-5">
                        <Button severity="secondary" @click="activateCallback('2')">
                            <ArrowLeft />
                            Back
                        </Button>
                    </div>
                </StepPanel>
            </StepPanels>
        </Stepper>
    </div>
</template>

<script setup>
import ArrowLeft from '@primeicons/vue/arrow-left';
import ArrowRight from '@primeicons/vue/arrow-right';
<\/script>
```

## Steps Only

Use Stepper with a StepList only for custom requirements where a progress indicator is needed.

```vue
<template>
    <div class="flex justify-center">
        <Stepper value="1" class="basis-200 min-w-0">
            <StepList>
                <Step value="1">Design</Step>
                <Step value="2">Development</Step>
                <Step value="3">QA</Step>
            </StepList>
        </Stepper>
    </div>
</template>
```

## Template

Custom content for a step is defined with the default slot. The optional as property controls the default container element of a step, for example setting it to a button renders a button for the header instead of a div. The asChild option enables the headless mode for further customization by passing callbacks and properties to implement your own step.

```vue
<template>
    <div class="flex justify-center">
        <Stepper v-model:value="activeStep" class="basis-160 min-w-0">
            <StepList>
                <Step v-slot="{ activateCallback, value, a11yAttrs }" asChild :value="1">
                    <div class="flex flex-row flex-auto gap-2" v-bind="a11yAttrs.root">
                        <button class="bg-transparent border-0 inline-flex flex-col gap-2" @click="activateCallback" v-bind="a11yAttrs.header">
                            <span
                                :class="[ 'rounded-full border-2 w-12 h-12 inline-flex items-center justify-center', { 'bg-primary text-primary-contrast border-primary': value <= activeStep, 'border-surface-200 dark:border-surface-700': value > activeStep } ]"
                            >
                                <User />
                            </span>
                        </button>
                        <Divider />
                    </div>
                </Step>
                <Step v-slot="{ activateCallback, value, a11yAttrs }" asChild :value="2">
                    <div class="flex flex-row flex-auto gap-2 pl-2" v-bind="a11yAttrs.root">
                        <button class="bg-transparent border-0 inline-flex flex-col gap-2" @click="activateCallback" v-bind="a11yAttrs.header">
                            <span
                                :class="[ 'rounded-full border-2 w-12 h-12 inline-flex items-center justify-center', { 'bg-primary text-primary-contrast border-primary': value <= activeStep, 'border-surface-200 dark:border-surface-700': value > activeStep } ]"
                            >
                                <Star />
                            </span>
                        </button>
                        <Divider />
                    </div>
                </Step>
                <Step v-slot="{ activateCallback, value, a11yAttrs }" asChild :value="3">
                    <div class="flex flex-row pl-2" v-bind="a11yAttrs.root">
                        <button class="bg-transparent border-0 inline-flex flex-col gap-2" @click="activateCallback" v-bind="a11yAttrs.header">
                            <span
                                :class="[ 'rounded-full border-2 w-12 h-12 inline-flex items-center justify-center', { 'bg-primary text-primary-contrast border-primary': value <= activeStep, 'border-surface-200 dark:border-surface-700': value > activeStep } ]"
                            >
                                <IdCard />
                            </span>
                        </button>
                    </div>
                </Step>
            </StepList>
            <StepPanels>
                <StepPanel v-slot="{ activateCallback }" :value="1">
                    <div class="flex flex-col gap-2 mx-auto" style="min-height: 16rem; max-width: 20rem">
                        <div class="text-center mt-4 mb-4 text-lg font-semibold">Create your account</div>
                        <div class="field">
                            <InputText id="input" v-model="name" type="text" placeholder="Name" fluid />
                        </div>
                        <div class="field">
                            <InputText id="email" v-model="email" type="email" placeholder="Email" fluid />
                        </div>
                        <div class="field">
                            <Password v-model="password" placeholder="Password" fluid />
                        </div>
                    </div>
                    <div class="flex pt-5 justify-end">
                        <Button @click="activateCallback(2)">
                            Next
                            <ArrowRight />
                        </Button>
                    </div>
                </StepPanel>
                <StepPanel v-slot="{ activateCallback }" :value="2">
                    <div class="flex flex-col gap-2 mx-auto" style="min-height: 16rem; max-width: 24rem">
                        <div class="text-center mt-4 mb-4 text-lg font-semibold">Choose your interests</div>
                        <div class="flex flex-wrap justify-center gap-4">
                            <ToggleButton v-model="option1" onLabel="Nature" offLabel="Nature" />
                            <ToggleButton v-model="option2" onLabel="Art" offLabel="Art" />
                            <ToggleButton v-model="option3" onLabel="Music" offLabel="Music" />
                            <ToggleButton v-model="option4" onLabel="Design" offLabel="Design" />
                            <ToggleButton v-model="option5" onLabel="Photography" offLabel="Photography" />
                            <ToggleButton v-model="option6" onLabel="Movies" offLabel="Movies" />
                            <ToggleButton v-model="option7" onLabel="Sports" offLabel="Sports" />
                            <ToggleButton v-model="option8" onLabel="Gaming" offLabel="Gaming" />
                            <ToggleButton v-model="option9" onLabel="Traveling" offLabel="Traveling" />
                            <ToggleButton v-model="option10" onLabel="Dancing" offLabel="Dancing" />
                        </div>
                    </div>
                    <div class="flex pt-5 justify-between">
                        <Button severity="secondary" @click="activateCallback(1)">
                            <ArrowLeft />
                            Back
                        </Button>
                        <Button @click="activateCallback(3)">
                            Next
                            <ArrowRight />
                        </Button>
                    </div>
                </StepPanel>
                <StepPanel v-slot="{ activateCallback }" :value="3">
                    <div class="flex flex-col gap-2 mx-auto" style="min-height: 16rem; max-width: 24rem">
                        <div class="text-center mt-4 mb-4 text-lg font-semibold">Account created successfully</div>
                        <div class="flex justify-center">
                            <img alt="logo" src="https://primefaces.org/cdn/primevue/images/stepper/content.svg" />
                        </div>
                    </div>
                    <div class="flex pt-5 justify-start">
                        <Button severity="secondary" @click="activateCallback(2)">
                            <ArrowLeft />
                            Back
                        </Button>
                    </div>
                </StepPanel>
            </StepPanels>
        </Stepper>
    </div>
</template>

<script setup>
import ArrowLeft from '@primeicons/vue/arrow-left';
import ArrowRight from '@primeicons/vue/arrow-right';
import IdCard from '@primeicons/vue/id-card';
import Star from '@primeicons/vue/star';
import User from '@primeicons/vue/user';
import { ref } from 'vue';

const activeStep = ref(1);
const name = ref();
const email = ref();
const password = ref();
const option1 = ref(false);
const option2 = ref(false);
const option3 = ref(false);
const option4 = ref(false);
const option5 = ref(false);
const option6 = ref(false);
const option7 = ref(false);
const option8 = ref(false);
const option9 = ref(false);
const option10 = ref(false);

<\/script>
```

## Accessibility

Screen Reader Stepper container is defined with the tablist role, as any attribute is passed to the container element aria-labelledby can be optionally used to specify an element to describe the Stepper. Each stepper header has a tab role and aria-controls to refer to the corresponding stepper content element. The content element of each stepper has tabpanel role, an id to match the aria-controls of the header and aria-labelledby reference to the header as the accessible name. Tab Header Keyboard Support Key Function tab Moves focus through the header. enter Activates the focused stepper header. space Activates the focused stepper header.

## Stepper API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| value | string \| number | null | Active value of stepper. |
| linear | boolean | false | Whether the steps are clickable or not. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | StepperPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| separator | StepperPassThroughOptionType | Used to pass attributes to the separator's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-stepper | Class name of the root element |
| p-stepper-separator | Class name of the separator element |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| stepper.transition.duration | --p-stepper-transition-duration | Transition duration of root |
| stepper.separator.background | --p-stepper-separator-background | Background of separator |
| stepper.separator.active.background | --p-stepper-separator-active-background | Active background of separator |
| stepper.separator.margin | --p-stepper-separator-margin | Margin of separator |
| stepper.separator.size | --p-stepper-separator-size | Size of separator |
| stepper.step.padding | --p-stepper-step-padding | Padding of step |
| stepper.step.gap | --p-stepper-step-gap | Gap of step |
| stepper.step.header.padding | --p-stepper-step-header-padding | Padding of step header |
| stepper.step.header.border.radius | --p-stepper-step-header-border-radius | Border radius of step header |
| stepper.step.header.focus.ring.width | --p-stepper-step-header-focus-ring-width | Focus ring width of step header |
| stepper.step.header.focus.ring.style | --p-stepper-step-header-focus-ring-style | Focus ring style of step header |
| stepper.step.header.focus.ring.color | --p-stepper-step-header-focus-ring-color | Focus ring color of step header |
| stepper.step.header.focus.ring.offset | --p-stepper-step-header-focus-ring-offset | Focus ring offset of step header |
| stepper.step.header.focus.ring.shadow | --p-stepper-step-header-focus-ring-shadow | Focus ring shadow of step header |
| stepper.step.header.gap | --p-stepper-step-header-gap | Gap of step header |
| stepper.step.title.color | --p-stepper-step-title-color | Color of step title |
| stepper.step.title.active.color | --p-stepper-step-title-active-color | Active color of step title |
| stepper.step.title.font.weight | --p-stepper-step-title-font-weight | Font weight of step title |
| stepper.step.title.font.size | --p-stepper-step-title-font-size | Font size of step title |
| stepper.step.number.background | --p-stepper-step-number-background | Background of step number |
| stepper.step.number.active.background | --p-stepper-step-number-active-background | Active background of step number |
| stepper.step.number.border.color | --p-stepper-step-number-border-color | Border color of step number |
| stepper.step.number.active.border.color | --p-stepper-step-number-active-border-color | Active border color of step number |
| stepper.step.number.color | --p-stepper-step-number-color | Color of step number |
| stepper.step.number.active.color | --p-stepper-step-number-active-color | Active color of step number |
| stepper.step.number.size | --p-stepper-step-number-size | Size of step number |
| stepper.step.number.font.size | --p-stepper-step-number-font-size | Font size of step number |
| stepper.step.number.font.weight | --p-stepper-step-number-font-weight | Font weight of step number |
| stepper.step.number.border.radius | --p-stepper-step-number-border-radius | Border radius of step number |
| stepper.step.number.shadow | --p-stepper-step-number-shadow | Shadow of step number |
| stepper.steppanels.padding | --p-stepper-steppanels-padding | Padding of steppanels |
| stepper.steppanel.background | --p-stepper-steppanel-background | Background of steppanel |
| stepper.steppanel.color | --p-stepper-steppanel-color | Color of steppanel |
| stepper.steppanel.padding | --p-stepper-steppanel-padding | Padding of steppanel |
| stepper.steppanel.indent | --p-stepper-steppanel-indent | Indent of steppanel |

## Step List API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | StepListPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-steplist | Class name of the root element |

## Step Panels API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | StepPanelsPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-steppanels | Class name of the root element |

## Step Item API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| value | string \| number | - | Value of step. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | StepItemPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-stepitem | Class name of the root element |

## Step API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| value | string \| number | - | Value of step. |
| disabled | boolean | false | Whether the step is disabled. |
| as | string \| Component | BUTTON | Use to change the HTML tag of root element. |
| asChild | boolean | false | When enabled, it changes the default rendered element for the one passed as a child element. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | StepPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| header | StepPassThroughOptionType | Used to pass attributes to the header's DOM element. |
| number | StepPassThroughOptionType | Used to pass attributes to the number's DOM element. |
| title | StepPassThroughOptionType | Used to pass attributes to the title's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-step | Class name of the root element |
| p-step-header | Class name of the header element |
| p-step-number | Class name of the number element |
| p-step-title | Class name of the title element |

## Step Panel API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| value | string \| number | - | Value of step. |
| as | string \| Component | BUTTON | Use to change the HTML tag of root element. |
| asChild | boolean | false | When enabled, it changes the default rendered element for the one passed as a child element. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | StepPanelPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| contentWrapper | StepPanelPassThroughOptionType | Used to pass attributes to the content's wrapper DOM element. |
| content | StepPanelPassThroughOptionType | Used to pass attributes to the content DOM element. |
| transition | StepPanelPassThroughOptionType | Used to control Vue Transition API. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-steppanel | Class name of the root element |
