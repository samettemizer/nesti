# Timeline

Timeline visualizes a series of chained events.

## Basic

Timeline receives the events with the value property as a collection of arbitrary objects. In addition, content template is required to display the representation of an event. Example below is a sample events array that is used throughout the documentation.

```vue
<template>
    <Timeline :value="events">
        <template #content="slotProps">
            <div class="text-sm leading-4">
                {{ slotProps.item.status }}
            </div>
        </template>
    </Timeline>
</template>

<script setup>
import { ref } from 'vue';

const events = ref([{ status: 'Ordered' }, { status: 'Processing' }, { status: 'Shipped' }, { status: 'Delivered' }]);
<\/script>
```

## Alignment

Content location relative the line is defined with the align property.

```vue
<template>
    <div class="flex flex-wrap gap-12">
        <Timeline :value="events" class="w-full md:w-80">
            <template #content="slotProps">
                <div class="text-sm leading-4">
                    {{ slotProps.item.status }}
                </div>
            </template>
        </Timeline>

        <Timeline :value="events" align="right" class="w-full md:w-80">
            <template #content="slotProps">
                <div class="text-sm leading-4">
                    {{ slotProps.item.status }}
                </div>
            </template>
        </Timeline>

        <Timeline :value="events" align="alternate" class="w-full md:w-80">
            <template #content="slotProps">
                <div class="text-sm leading-4">
                    {{ slotProps.item.status }}
                </div>
            </template>
        </Timeline>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const events = ref([{ status: 'Ordered' }, { status: 'Processing' }, { status: 'Shipped' }, { status: 'Delivered' }]);
<\/script>
```

## Opposite

Additional content at the other side of the line can be provided with the opposite property.

```vue
<template>
    <Timeline :value="events">
        <template #opposite="slotProps">
            <div class="text-xs leading-4 text-surface-500 dark:text-surface-400">{{ slotProps.item.date }}</div>
        </template>
        <template #content="slotProps">
            <div class="text-sm leading-4">
                {{ slotProps.item.status }}
            </div>
        </template>
    </Timeline>
</template>

<script setup>
import { ref } from 'vue';

const events = ref([
    { status: 'Ordered', date: '15/10/2026 10:30' },
    { status: 'Processing', date: '15/10/2026 14:00' },
    { status: 'Shipped', date: '15/10/2026 16:15' },
    { status: 'Delivered', date: '16/10/2026 10:00' }
]);
<\/script>
```

## Horizontal

TimeLine orientation is controlled with the layout property, default is vertical having horizontal as the alternative.

```vue
<template>
    <div class="flex flex-col gap-4">
        <Timeline :value="events" layout="horizontal" align="top">
            <template #content="slotProps">
                <span class="text-sm">
                    {{ slotProps.item }}
                </span>
            </template>
        </Timeline>

        <Timeline :value="events" layout="horizontal" align="bottom">
            <template #content="slotProps">
                <span class="text-sm">
                    {{ slotProps.item }}
                </span>
            </template>
        </Timeline>

        <Timeline :value="events" layout="horizontal" align="alternate">
            <template #opposite> &nbsp; </template>
            <template #content="slotProps">
                <span class="text-sm">
                    {{ slotProps.item }}
                </span>
            </template>
        </Timeline>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const events = ref(['2026', '2027', '2028', '2029']);
<\/script>
```

## Custom

Sample implementation with custom content, styled markers, and rich event cards.

```vue
<template>
    <Timeline :value="events" align="alternate" class="w-full @container" :pt="{ event: { class: '@max-[480px]:flex-row!' }, eventOpposite: { class: '@max-[480px]:hidden' }, eventContent: { class: '@max-[480px]:text-left!' }, eventConnector: { class: 'mb-4' } }">
        <template #opposite="slotProps">
            <div class="font-medium text-surface-700 dark:text-surface-200">{{ slotProps.item.date }}</div>
            <div class="text-sm text-surface-500 dark:text-surface-400">{{ slotProps.item.time }}</div>
        </template>
        <template #marker="slotProps">
            <span :class="'flex items-center justify-center w-12 h-12 rounded-full text-white shadow-lg ' + slotProps.item.color">
                <component :is="slotProps.icon" class="w-4.5! h-4.5!" />
            </span>
        </template>
        <template #content="slotProps">
            <div class="p-5 rounded-xl bg-surface-0 dark:bg-surface-800 border border-surface-200 dark:border-surface-700 shadow-sm mb-4 text-left">
                <div class="hidden @max-[480px]:block mb-2 text-sm text-surface-500 dark:text-surface-400">{{ slotProps.item.date }} · {{ slotProps.item.time }}</div>
                <div class="flex items-center gap-3 mb-3">
                    <Avatar :label="slotProps.item.user" shape="circle" class="bg-primary/10! text-primary! font-semibold!" />
                    <span class="font-bold text-surface-900 dark:text-surface-0">{{ slotProps.item.status }}</span>
                </div>
                <span class="text-surface-600 dark:text-surface-300 text-sm leading-relaxed">{{ slotProps.item.description }}</span>
                <ul v-if="slotProps.item.details" class="mt-3 space-y-1">
                    <li v-for="detail in slotProps.item.details" :key="detail" class="text-sm text-surface-500 dark:text-surface-400 flex items-center gap-2">
                        <Box :size="12" />
                        {{ detail }}
                    </li>
                </ul>
                <div v-if="slotProps.item.tracking" class="mt-4 p-3 rounded-lg bg-surface-100 dark:bg-surface-700 flex items-center justify-between">
                    <span class="text-sm text-surface-600 dark:text-surface-300 flex items-center">
                        <MapMarker class="mr-2 shrink-0" />
                        Tracking: {{ slotProps.item.tracking }}
                    </span>
                    <Button variant="text" size="small">Track</Button>
                </div>
            </div>
        </template>
    </Timeline>
</template>

<script setup>
import { ref } from 'vue';
import Box from '@primeicons/vue/box';
import CheckCircle from '@primeicons/vue/check-circle';
import CreditCard from '@primeicons/vue/credit-card';
import MapMarker from '@primeicons/vue/map-marker';
import ShoppingCart from '@primeicons/vue/shopping-cart';
import Truck from '@primeicons/vue/truck';

const events = ref([
    {
        status: 'Order Placed',
        date: 'Oct 15, 2026',
        time: '10:30 AM',
        icon: ShoppingCart,
        color: 'bg-blue-500',
        user: 'JD',
        description: 'Your order #12345 has been confirmed and is being prepared for processing.',
        details: ['2x Wireless Headphones', '1x Phone Case', '1x USB-C Cable']
    },
    {
        status: 'Payment Confirmed',
        date: 'Oct 15, 2026',
        time: '10:32 AM',
        icon: CreditCard,
        color: 'bg-green-500',
        user: 'SY',
        description: 'Payment of $149.99 was successfully processed via Credit Card ending in 4242.'
    },
    {
        status: 'Shipped',
        date: 'Oct 16, 2026',
        time: '02:15 PM',
        icon: Truck,
        color: 'bg-orange-500',
        user: 'MK',
        description: 'Package has been handed to the carrier and is on its way.',
        tracking: 'TRK-892374651'
    },
    {
        status: 'Delivered',
        date: 'Oct 18, 2026',
        time: '11:20 AM',
        icon: CheckCircle,
        color: 'bg-lime-500',
        user: 'JD',
        description: 'Package was delivered and signed for at the front door.'
    }
]);
<\/script>
```

## Interactive

Build interactive step-based workflows with progress tracking and state management.

```vue
<template>
    <div class="flex flex-col gap-6">
        <div class="flex items-center justify-between">
            <div>
                <h3 class="text-lg font-semibold m-0">Onboarding Progress</h3>
                <p class="text-surface-500 text-sm mt-1 mb-0">{{ completedSteps.length }} of {{ allSteps.length }} steps completed</p>
            </div>
            <Button variant="outlined" size="small" @click="handleReset()">
                <Refresh />
                Reset
            </Button>
        </div>
        <div class="w-full bg-surface-200 dark:bg-surface-700 rounded-full h-2">
            <div class="bg-primary rounded-full h-2 transition-all duration-500" :style="{ width: (completedSteps.length / allSteps.length) * 100 + '%' }"></div>
        </div>
        <Timeline :value="allSteps">
            <template #marker="slotProps">
                <button
                    type="button"
                    :class="
                        'w-10 h-10 rounded-full flex items-center justify-center border-none transition-all duration-300 ' +
                        (getStepStatus(slotProps.item.id) === 'completed'
                            ? 'bg-green-500 text-white cursor-default'
                            : getStepStatus(slotProps.item.id) === 'current'
                              ? 'bg-primary text-primary-contrast cursor-pointer hover:scale-110 animate-pulse'
                              : 'bg-surface-200 dark:bg-surface-700 text-surface-400 cursor-not-allowed')
                    "
                    :disabled="getStepStatus(slotProps.item.id) !== 'current'"
                    @click="handleComplete(slotProps.item.id)"
                >
                    <Check v-if="getStepStatus(slotProps.item.id) === 'completed'" />
                    <component :is="slotProps.icon" v-else />
                </button>
            </template>
            <template #content="slotProps">
                <div :class="'p-3 rounded-lg transition-all duration-300 ' + (getStepStatus(slotProps.item.id) === 'completed' ? 'bg-green-50 dark:bg-green-900/20' : getStepStatus(slotProps.item.id) === 'current' ? 'bg-primary/10' : 'opacity-50')">
                    <p :class="'m-0 font-medium ' + (getStepStatus(slotProps.item.id) === 'completed' ? 'text-green-700 dark:text-green-400 line-through' : getStepStatus(slotProps.item.id) === 'current' ? 'text-primary' : 'text-surface-500')">
                        {{ slotProps.item.label }}
                    </p>
                    <p v-if="getStepStatus(slotProps.item.id) === 'current'" class="text-xs text-surface-500 mt-1 mb-0">Click the marker to complete</p>
                </div>
            </template>
        </Timeline>
        <div v-if="completedSteps.length === allSteps.length"
            class="p-4 rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 flex flex-col items-center gap-2">
            <CheckCircle size="24" class="text-green-500" />
            <div class="font-semibold text-green-700 dark:text-green-400">Onboarding Complete!</div>
            <span class="text-sm text-green-600 dark:text-green-500 leading-none">You've completed all the steps.</span>
        </div>
    </div>
</template>

<script setup>
import { ref } from 'vue';
import Check from '@primeicons/vue/check';
import CheckCircle from '@primeicons/vue/check-circle';
import Envelope from '@primeicons/vue/envelope';
import IdCard from '@primeicons/vue/id-card';
import Refresh from '@primeicons/vue/refresh';
import ShoppingBag from '@primeicons/vue/shopping-bag';
import Star from '@primeicons/vue/star';
import UserPlus from '@primeicons/vue/user-plus';

const allSteps = ref([
    { id: 1, label: 'Account Created', icon: UserPlus },
    { id: 2, label: 'Email Verified', icon: Envelope },
    { id: 3, label: 'Profile Completed', icon: IdCard },
    { id: 4, label: 'First Purchase', icon: ShoppingBag },
    { id: 5, label: 'Review Posted', icon: Star }
]);

const completedSteps = ref([1]);
const currentStep = ref(2);

const handleComplete = (stepId) => {
    if (stepId === currentStep.value) {
        completedSteps.value = [...completedSteps.value, stepId];
        currentStep.value++;
    }
};

const handleReset = () => {
    completedSteps.value = [1];
    currentStep.value = 2;
};

const getStepStatus = (stepId) => {
    if (completedSteps.value.includes(stepId)) {
        return 'completed';
    }
    if (stepId === currentStep.value) {
        return 'current';
    }
    return 'pending';
};
<\/script>
```

## Activity Feed

Display real-time activity streams with user avatars and contextual information.

```vue
<template>
    <div class="max-w-2xl">
        <div class="flex items-center gap-3 mb-6">
            <History :size="16" class="text-surface-500" />
            <span class="text-lg font-semibold text-surface-900 dark:text-surface-0">Recent Activity</span>
        </div>
        <Timeline :value="activities">
            <template #opposite="slotProps">
                <span class="text-xs text-surface-400 dark:text-surface-500 whitespace-nowrap">{{ slotProps.item.time }}</span>
            </template>
            <template #marker="slotProps">
                <Avatar :label="slotProps.item.user.avatar" shape="circle" :class="slotProps.item.user.color + ' text-white! text-xs font-semibold'" />
            </template>
            <template #content="slotProps">
                <div class="pb-6">
                    <div class="flex items-center gap-2 flex-wrap">
                        <span class="font-medium text-surface-900 dark:text-surface-0">{{ slotProps.item.user.name }}</span>
                        <span class="text-surface-500 dark:text-surface-400">{{ slotProps.item.action }}</span>
                        <span class="font-medium text-primary">{{ slotProps.item.target }}</span>
                        <template v-if="slotProps.item.repo">
                            <span class="text-surface-500 dark:text-surface-400">to</span>
                            <code class="px-2 py-0.5 rounded bg-surface-100 dark:bg-surface-800 text-sm font-mono text-surface-700 dark:text-surface-300">{{ slotProps.item.repo }}</code>
                        </template>
                    </div>
                    <p v-if="slotProps.item.description" class="mt-2 text-sm text-surface-600 dark:text-surface-400">{{ slotProps.item.description }}</p>
                    <div v-if="slotProps.item.details" class="mt-3 p-3 rounded-lg bg-surface-50 dark:bg-surface-800 border border-surface-200 dark:border-surface-700">
                        <ul class="space-y-1">
                            <li v-for="detail in slotProps.item.details" :key="detail" class="text-sm text-surface-600 dark:text-surface-400 font-mono flex items-start gap-2">
                                <Minus class="text-xs mt-1.5 text-surface-400" />
                                {{ detail }}
                            </li>
                        </ul>
                    </div>
                </div>
            </template>
        </Timeline>
    </div>
</template>

<script setup>
import { ref } from 'vue';
import History from '@primeicons/vue/history';
import Minus from '@primeicons/vue/minus';

const activities = ref([
    {
        id: 1,
        user: { name: 'Sarah Chen', avatar: 'SC', color: 'bg-violet-500!' },
        action: 'pushed',
        target: '3 commits',
        repo: 'main',
        time: '2 minutes ago',
        details: ['fix: resolve memory leak in useEffect', 'feat: add dark mode toggle', 'chore: update dependencies']
    },
    {
        id: 2,
        user: { name: 'Alex Kumar', avatar: 'AK', color: 'bg-blue-500!' },
        action: 'opened',
        target: 'pull request #142',
        repo: 'feature/auth',
        time: '15 minutes ago',
        description: 'Implement OAuth2 authentication flow'
    },
    {
        id: 3,
        user: { name: 'Maya Johnson', avatar: 'MJ', color: 'bg-emerald-500!' },
        action: 'commented on',
        target: 'issue #89',
        time: '1 hour ago',
        description: "I've investigated this bug and found the root cause. Working on a fix now."
    },
    {
        id: 4,
        user: { name: 'David Park', avatar: 'DP', color: 'bg-amber-500!' },
        action: 'merged',
        target: 'pull request #138',
        repo: 'main',
        time: '3 hours ago'
    },
    {
        id: 5,
        user: { name: 'Emma Wilson', avatar: 'EW', color: 'bg-rose-500!' },
        action: 'created',
        target: 'release v2.4.0',
        time: '5 hours ago',
        description: 'Performance improvements and bug fixes'
    }
]);
<\/script>
```

## Accessibility

Screen Reader Timeline uses a semantic ordered list element to list the events. No specific role is enforced, still you may use any aria role and attributes as any valid attribute is passed to the list element. Keyboard Support Component does not include any interactive elements.

## Timeline API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| value | any[] | - | An array of events to display. |
| align | any | left | Position of the timeline bar relative to the content. |
| layout | any | horizontal | Orientation of the timeline. |
| dataKey | string | - | Name of the field that uniquely identifies the a record in the data. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | TimelinePassThroughOptionType | Used to pass attributes to the root's DOM element. |
| event | TimelinePassThroughOptionType | Used to pass attributes to the event's DOM element. |
| eventOpposite | TimelinePassThroughOptionType | Used to pass attributes to the event opposite's DOM element. |
| eventSeparator | TimelinePassThroughOptionType | Used to pass attributes to the event separator's DOM element. |
| eventMarker | TimelinePassThroughOptionType | Used to pass attributes to the event marker's DOM element. |
| eventConnector | TimelinePassThroughOptionType | Used to pass attributes to the event connector's DOM element. |
| eventContent | TimelinePassThroughOptionType | Used to pass attributes to the event content's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-timeline | Class name of the root element |
| p-timeline-event | Class name of the event element |
| p-timeline-event-opposite | Class name of the event opposite element |
| p-timeline-event-separator | Class name of the event separator element |
| p-timeline-event-marker | Class name of the event marker element |
| p-timeline-event-connector | Class name of the event connector element |
| p-timeline-event-content | Class name of the event content element |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| timeline.event.min.height | --p-timeline-event-min-height | Min height of event |
| timeline.horizontal.event.content.padding | --p-timeline-horizontal-event-content-padding | Event content padding of horizontal |
| timeline.vertical.event.content.padding | --p-timeline-vertical-event-content-padding | Event content padding of vertical |
| timeline.event.marker.size | --p-timeline-event-marker-size | Size of event marker |
| timeline.event.marker.border.radius | --p-timeline-event-marker-border-radius | Border radius of event marker |
| timeline.event.marker.border.width | --p-timeline-event-marker-border-width | Border width of event marker |
| timeline.event.marker.background | --p-timeline-event-marker-background | Background of event marker |
| timeline.event.marker.border.color | --p-timeline-event-marker-border-color | Border color of event marker |
| timeline.event.marker.content.border.radius | --p-timeline-event-marker-content-border-radius | Content border radius of event marker |
| timeline.event.marker.content.size | --p-timeline-event-marker-content-size | Content size of event marker |
| timeline.event.marker.content.background | --p-timeline-event-marker-content-background | Content background of event marker |
| timeline.event.marker.content.inset.shadow | --p-timeline-event-marker-content-inset-shadow | Content inset shadow of event marker |
| timeline.event.connector.color | --p-timeline-event-connector-color | Color of event connector |
| timeline.event.connector.size | --p-timeline-event-connector-size | Size of event connector |
