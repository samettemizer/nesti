# Splitter

Splitter is utilized to separate and resize panels.

## Basic

Divides a layout into resizable panels with a draggable divider.

```vue
<template>
    <div>
        <Splitter class="h-60! max-w-lg mx-auto">
            <SplitterPanel class="flex items-center justify-center">
                <span class="px-2.5 py-1 rounded-md font-mono font-bold bg-surface-100 dark:bg-surface-800 text-color">1</span>
            </SplitterPanel>
            <SplitterPanel class="flex items-center justify-center">
                <span class="px-2.5 py-1 rounded-md font-mono font-bold bg-surface-100 dark:bg-surface-800 text-color">2</span>
            </SplitterPanel>
        </Splitter>
    </div>
</template>
```

## Vertical

Panels are stacked when layout is set to vertical .

```vue
<template>
    <div>
        <Splitter layout="vertical" class="h-60! max-w-lg mx-auto">
            <SplitterPanel class="flex items-center justify-center">
                <span class="px-2.5 py-1 rounded-md font-mono font-bold bg-surface-100 dark:bg-surface-800 text-color">1</span>
            </SplitterPanel>
            <SplitterPanel class="flex items-center justify-center">
                <span class="px-2.5 py-1 rounded-md font-mono font-bold bg-surface-100 dark:bg-surface-800 text-color">2</span>
            </SplitterPanel>
        </Splitter>
    </div>
</template>
```

## Size

Initial dimensions are percentage based and provided through sizes on Splitter. Per-panel constraints are configured with minSize and maxSize .

```vue
<template>
    <div>
        <Splitter :sizes="[25, 75]" class="h-60! max-w-lg mx-auto">
            <SplitterPanel :minSize="10" class="flex items-center justify-center">
                <span class="px-2.5 py-1 rounded-md font-mono font-bold bg-surface-100 dark:bg-surface-800 text-color">1</span>
            </SplitterPanel>
            <SplitterPanel class="flex items-center justify-center">
                <span class="px-2.5 py-1 rounded-md font-mono font-bold bg-surface-100 dark:bg-surface-800 text-color">2</span>
            </SplitterPanel>
        </Splitter>
    </div>
</template>
```

## Min Max Size

Each panel can declare a minSize and a maxSize in percentages. The splitter ensures the panel cannot shrink below minSize nor grow beyond maxSize during a resize.

```vue
<template>
    <div class="flex flex-col items-center gap-8 max-w-lg mx-auto">
        <Splitter class="w-full h-32!">
            <SplitterPanel :minSize="20" :maxSize="50" class="flex items-center justify-center">
                <span class="px-2.5 py-1 rounded-md font-mono font-bold bg-surface-100 dark:bg-surface-800 text-color">1</span>
            </SplitterPanel>
            <SplitterPanel class="flex items-center justify-center">
                <span class="px-2.5 py-1 rounded-md font-mono font-bold bg-surface-100 dark:bg-surface-800 text-color">2</span>
            </SplitterPanel>
        </Splitter>

        <Splitter class="w-full h-32!">
            <SplitterPanel :minSize="10" class="flex items-center justify-center">
                <span class="px-2.5 py-1 rounded-md font-mono font-bold bg-surface-100 dark:bg-surface-800 text-color">1</span>
            </SplitterPanel>
            <SplitterPanel :minSize="10" class="flex items-center justify-center">
                <span class="px-2.5 py-1 rounded-md font-mono font-bold bg-surface-100 dark:bg-surface-800 text-color">2</span>
            </SplitterPanel>
            <SplitterPanel :minSize="10" class="flex items-center justify-center">
                <span class="px-2.5 py-1 rounded-md font-mono font-bold bg-surface-100 dark:bg-surface-800 text-color">3</span>
            </SplitterPanel>
        </Splitter>
    </div>
</template>
```

## Collapsible

Adding collapsible to a panel allows it to snap to collapsedSize (default 0% ) once it is dragged past the halfway point between collapsedSize and minSize . Keyboard resize collapses immediately when the panel reaches minSize .

```vue
<template>
    <div class="flex flex-col items-center gap-8 max-w-lg mx-auto">
        <Splitter class="w-full h-32">
            <SplitterPanel :minSize="10" collapsible class="flex items-center justify-center">
                <span class="px-2.5 py-1 rounded-md font-mono font-bold bg-surface-100 dark:bg-surface-800 text-color">1</span>
            </SplitterPanel>
            <SplitterPanel class="flex items-center justify-center">
                <span class="px-2.5 py-1 rounded-md font-mono font-bold bg-surface-100 dark:bg-surface-800 text-color">2</span>
            </SplitterPanel>
        </Splitter>

        <Splitter class="w-full h-32">
            <SplitterPanel :minSize="20" :collapsedSize="5" collapsible class="flex items-center justify-center">
                <span class="px-2.5 py-1 rounded-md font-mono font-bold bg-surface-100 dark:bg-surface-800 text-color">1</span>
            </SplitterPanel>
            <SplitterPanel :minSize="10" class="flex items-center justify-center">
                <span class="px-2.5 py-1 rounded-md font-mono font-bold bg-surface-100 dark:bg-surface-800 text-color">2</span>
            </SplitterPanel>
        </Splitter>
    </div>
</template>
```

## Nested

Splitters can be nested by placing another Splitter inside a SplitterPanel.

```vue
<template>
    <div>
        <Splitter :sizes="[25, 75]" class="h-80 w-full max-w-lg mx-auto">
            <SplitterPanel :minSize="10" class="flex items-center justify-center">
                <span class="px-2.5 py-1 rounded-md font-mono font-bold bg-surface-100 dark:bg-surface-800 text-color">1</span>
            </SplitterPanel>
            <SplitterPanel>
                <Splitter :sizes="[50, 50]" layout="vertical">
                    <SplitterPanel class="flex items-center justify-center">
                        <span class="px-2.5 py-1 rounded-md font-mono font-bold bg-surface-100 dark:bg-surface-800 text-color">2</span>
                    </SplitterPanel>
                    <SplitterPanel>
                        <Splitter :sizes="[20, 80]">
                            <SplitterPanel class="flex items-center justify-center">
                                <span class="px-2.5 py-1 rounded-md font-mono font-bold bg-surface-100 dark:bg-surface-800 text-color">3</span>
                            </SplitterPanel>
                            <SplitterPanel class="flex items-center justify-center">
                                <span class="px-2.5 py-1 rounded-md font-mono font-bold bg-surface-100 dark:bg-surface-800 text-color">4</span>
                            </SplitterPanel>
                        </Splitter>
                    </SplitterPanel>
                </Splitter>
            </SplitterPanel>
        </Splitter>
    </div>
</template>
```

## Resize Events

Splitter emits resizestart , resize , and resizeend while a gutter is being dragged, and collapse whenever a collapsible panel snaps to or out of collapsedSize . Every event carries the current sizes.

```vue
<template>
    <div class="flex flex-col items-center gap-4 max-w-lg mx-auto">
        <div class="flex flex-col items-center gap-1 w-full text-sm font-mono text-surface-500">
            <div>onResizeStart: [{{ format(resizeStart) }}]</div>
            <div>onResize: [{{ format(resize) }}]</div>
            <div>onResizeEnd: [{{ format(resizeEnd) }}]</div>
            <div>onCollapse: {{ collapseLabel }}</div>
        </div>

        <Splitter
            class="w-full h-60!"
            @resizestart="(e) => (resizeStart = e.sizes)"
            @resize="(e) => (resize = e.sizes)"
            @resizeend="(e) => (resizeEnd = e.sizes)"
            @collapse="(e) => (collapseEvent = e)"
        >
            <SplitterPanel :minSize="15" collapsible class="flex items-center justify-center">
                <span class="px-2.5 py-1 rounded-md font-mono font-bold bg-surface-100 dark:bg-surface-800 text-color">1</span>
            </SplitterPanel>
            <SplitterPanel :minSize="25" collapsible class="flex items-center justify-center">
                <span class="px-2.5 py-1 rounded-md font-mono font-bold bg-surface-100 dark:bg-surface-800 text-color">2</span>
            </SplitterPanel>
        </Splitter>
    </div>
</template>

<script setup>
import { computed, ref } from 'vue';

const resizeStart = ref([50, 50]);
const resize = ref([50, 50]);
const resizeEnd = ref([50, 50]);
const collapseEvent = ref(null);

const format = (sizes) => sizes.map((s) => s.toFixed(1) + '%').join(', ');

const collapseLabel = computed(() => {
    if (!collapseEvent.value) return '–';

    return \`Panel \${collapseEvent.value.index} \${collapseEvent.value.collapsed ? 'collapsed' : 'expanded'} [\${format(collapseEvent.value.sizes)}]\`;
});
<\/script>
```

## Stateful

Binding the panel sizes with v-model:sizes turns the Splitter into a controlled component. Persisting the bound state to localStorage keeps the layout across page reloads. The built-in stateKey / stateStorage pair offers the same persistence without manual bookkeeping.

```vue
<template>
    <div>
        <Splitter v-model:sizes="sizes" class="h-60! max-w-lg mx-auto" @resizeend="persist">
            <SplitterPanel :minSize="10" class="flex items-center justify-center gap-2">
                <span class="px-2.5 py-1 rounded-md font-mono font-bold bg-surface-100 dark:bg-surface-800 text-color">1</span>
                <span class="text-sm text-muted-color tabular-nums">({{ sizes[0].toFixed(1) }}%)</span>
            </SplitterPanel>
            <SplitterPanel :minSize="10" class="flex items-center justify-center gap-2">
                <span class="px-2.5 py-1 rounded-md font-mono font-bold bg-surface-100 dark:bg-surface-800 text-color">2</span>
                <span class="text-sm text-muted-color tabular-nums">({{ sizes[1].toFixed(1) }}%)</span>
            </SplitterPanel>
        </Splitter>
    </div>
</template>

<script setup>
import { onMounted, ref } from 'vue';

const STORAGE_KEY = 'splitter-demo-sizes';
const sizes = ref([30, 70]);

onMounted(() => {
    const cached = localStorage.getItem(STORAGE_KEY);

    if (cached) sizes.value = JSON.parse(cached);
});

const persist = (event) => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(event.sizes));
};
<\/script>
```

## Disabled

When disabled is present on the splitter, every gutter becomes non-interactive. The splitter is rendered with data-disabled , which the theme uses to fade the gutter and turn off pointer interactions.

```vue
<template>
    <div class="flex flex-col items-center gap-8 max-w-lg mx-auto">
        <Splitter class="w-full h-32" disabled>
            <SplitterPanel class="flex items-center justify-center">
                <span class="px-2.5 py-1 rounded-md font-mono font-bold bg-surface-100 dark:bg-surface-800 text-color">1</span>
            </SplitterPanel>
            <SplitterPanel class="flex items-center justify-center">
                <span class="px-2.5 py-1 rounded-md font-mono font-bold bg-surface-100 dark:bg-surface-800 text-color">2</span>
            </SplitterPanel>
            <SplitterPanel class="flex items-center justify-center">
                <span class="px-2.5 py-1 rounded-md font-mono font-bold bg-surface-100 dark:bg-surface-800 text-color">3</span>
            </SplitterPanel>
        </Splitter>
    </div>
</template>
```

## Custom

The default appearance is fully overridable through Tailwind utilities on the panels and the pt API on the gutter. Below, panels become colored badge containers and the gutter is rendered as a thin rounded bar.

```vue
<template>
    <div>
        <Splitter
            class="h-60! max-w-lg mx-auto border-none! gap-0.5! bg-transparent!"
            :pt="{
                gutter: { class: 'w-1.5! rounded-xs!' }
            }"
        >
            <SplitterPanel class="flex items-center justify-center border border-blue-500 bg-blue-500/10 rounded-sm text-blue-500">
                <span class="px-2.5 py-1 rounded-md font-mono font-bold bg-current/20">1</span>
            </SplitterPanel>
            <SplitterPanel class="flex items-center justify-center border border-purple-500 bg-purple-500/10 rounded-sm text-purple-500">
                <span class="px-2.5 py-1 rounded-md font-mono font-bold bg-current/20">2</span>
            </SplitterPanel>
        </Splitter>
    </div>
</template>
```

## Advanced

A real-world layout combining a collapsible navigation pane, a custom gutter handle and a viewport that adapts to the current sizes. The pane switches to a compact list once its width drops below 28%.

```vue
<template>
    <div>
        <Splitter
            v-model:sizes="sizes"
            class="h-150!"
            :pt="{
                gutterHandle: { class: 'absolute! inset-y-0! h-full! rounded-none w-2! left-1/2! -translate-x-1/2! bg-surface-200! dark:bg-surface-700! hover:opacity-100! data-[resizing]:opacity-100! opacity-0! transition-opacity! delay-100!' },
                gutter: { class: 'relative!' }
            }"
            @resizeend="(e) => (sizes = e.sizes)"
        >
            <SplitterPanel :minSize="20" collapsible>
                <ul class="list-none m-0 p-0 w-full">
                    <li
                        v-for="(mail, i) in mails"
                        :key="i"
                        :class="[ 'px-4 py-3 cursor-pointer border-b border-surface-100 dark:border-surface-800 transition-colors', selected === i ? 'bg-primary-50 dark:bg-primary-950' : 'hover:bg-surface-50 dark:hover:bg-surface-800' ]"
                        @click="selected = i"
                    >
                        <div class="flex items-center justify-between gap-2">
                            <span class="font-semibold text-surface-900 dark:text-surface-0 text-sm truncate">{{ mail.name }}</span>
                            <span class="text-surface-400 text-xs shrink-0">{{ mail.time }}</span>
                        </div>
                        <template v-if="!isCompact">
                            <div class="text-surface-700 dark:text-surface-200 text-sm font-medium mt-1 mb-1">{{ mail.title }}</div>
                            <div class="text-surface-400 dark:text-surface-500 text-xs line-clamp-1">{{ mail.description }}</div>
                        </template>
                    </li>
                </ul>
            </SplitterPanel>
            <SplitterPanel :minSize="30">
                <div class="p-6">
                    <div class="flex items-start justify-between gap-4 mb-2">
                        <h2 class="text-lg font-semibold text-surface-900 dark:text-surface-0 m-0!">{{ mails[selected].title }}</h2>
                        <span class="text-surface-400 text-xs shrink-0 pt-1">{{ mails[selected].time }}</span>
                    </div>
                    <span class="text-surface-400 text-sm">{{ mails[selected].name }}</span>
                    <p class="text-surface-600 dark:text-surface-300 text-sm leading-relaxed mt-4 m-0!">{{ mails[selected].description }}</p>
                </div>
            </SplitterPanel>
        </Splitter>
    </div>
</template>

<script setup>
import { computed, ref } from 'vue';

const selected = ref(0);
const sizes = ref([35, 65]);
const isCompact = computed(() => sizes.value[0] < 28);

const mails = [
    { name: 'Amy Elsner', title: 'Q1 Marketing Report', description: "Hi team, I've attached the Q1 marketing report. Please review the campaign metrics and share your feedback before our meeting on Friday.", time: '10:24 AM' },
    { name: 'Bernardo Dominic', title: 'Design System Update', description: "The new design tokens are ready for review. I've updated the color palette and typography scale based on our last discussion.", time: '9:15 AM' },
    { name: 'Ioni Bowcher', title: 'Sprint Retrospective Notes', description: "Here are the notes from yesterday's retro. Key takeaways: improve code review turnaround and schedule more pair programming sessions.", time: 'Yesterday' },
    { name: 'Stephen Shaw', title: 'Server Migration Plan', description: 'The migration to the new cloud infrastructure is scheduled for next weekend. Please ensure all services have proper health checks configured.', time: 'Yesterday' },
    { name: 'Elwin Sharvill', title: 'New Component Library Release', description: 'Version 4.0 of the component library is now available. Major changes include accessibility improvements and new theming capabilities.', time: 'Monday' }
];
<\/script>
```

## Accessibility

Screen Reader Splitter gutter defines separator as the role with aria-orientation set to either horizontal or vertical. Each gutter provides aria-valuenow , aria-valuemin , and aria-valuemax to communicate panel sizes. Adjacent panels are linked via aria-controls . Keyboard Support Key Function tab Moves focus through the splitter bar. down arrow Moves a vertical splitter down. up arrow Moves a vertical splitter up. left arrow Moves a horizontal splitter to the left. right arrow Moves a horizontal splitter to the right.

## Splitter API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| layout | any | horizontal | Orientation of the panels. |
| gutterSize | number | 4 | Size of the divider in pixels. |
| stateKey | string | - | Storage identifier of a stateful Splitter. |
| stateStorage | any | session | Defines where a stateful splitter keeps its state, valid values are 'session' for sessionStorage and 'local' for localStorage. |
| step | number | 5 | Step factor to increment/decrement the size of the panels while pressing the arrow keys. |
| disabled | boolean | false | When present, it disables the component and prevents resizing. |
| sizes | number[] | - | Sizes of the panels as percentages. When provided, makes the component controlled via  `v-model:sizes` . |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | SplitterPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| gutter | SplitterPassThroughOptionType | Used to pass attributes to the gutter's DOM element. |
| gutterHandle | SplitterPassThroughOptionType | Used to pass attributes to the gutter handle's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-splitter | Class name of the root element |
| p-splitter-gutter | Class name of the gutter element |
| p-splitter-gutter-handle | Class name of the gutter handle element |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| splitter.background | --p-splitter-background | Background of root |
| splitter.border.color | --p-splitter-border-color | Border color of root |
| splitter.color | --p-splitter-color | Color of root |
| splitter.transition.duration | --p-splitter-transition-duration | Transition duration of root |
| splitter.gutter.background | --p-splitter-gutter-background | Background of gutter |
| splitter.handle.size | --p-splitter-handle-size | Size of handle |
| splitter.handle.background | --p-splitter-handle-background | Background of handle |
| splitter.handle.border.radius | --p-splitter-handle-border-radius | Border radius of handle |
| splitter.handle.focus.ring.width | --p-splitter-handle-focus-ring-width | Focus ring width of handle |
| splitter.handle.focus.ring.style | --p-splitter-handle-focus-ring-style | Focus ring style of handle |
| splitter.handle.focus.ring.color | --p-splitter-handle-focus-ring-color | Focus ring color of handle |
| splitter.handle.focus.ring.offset | --p-splitter-handle-focus-ring-offset | Focus ring offset of handle |
| splitter.handle.focus.ring.shadow | --p-splitter-handle-focus-ring-shadow | Focus ring shadow of handle |

## Splitter Panel API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| size | number | - | Size of the element relative to 100%. |
| minSize | number | 0 | Minimum size of the element relative to 100%. |
| maxSize | number | 100 | Maximum size of the element relative to 100%. |
| collapsible | boolean | false | When enabled, the panel can collapse below  `minSize`  to  `collapsedSize` . |
| collapsedSize | number | 0 | Size of the panel when collapsed, relative to 100%. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Slots

| Name |Parameters |Description |
| --- | --- | --- |
| default | Function |  |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | SplitterPanelPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-splitter-panel | Class name of the root element |
