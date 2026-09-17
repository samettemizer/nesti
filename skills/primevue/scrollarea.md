# ScrollArea

ScrollArea is a cross browser, lightweight and themable alternative to native browser scrollbar.

## Basic

A custom scrollable container with styled scrollbars.

```vue
<template>
    <div class="max-w-56 w-full mx-auto">
        <div class="text-surface-500 dark:text-surface-400 font-medium text-sm uppercase font-mono tracking-tight mb-2">Automobiles</div>
        <ScrollArea class="h-72">
            <ScrollAreaViewport>
                <ScrollAreaContent class="space-y-2">
                    <span v-for="car in automobiles" :key="car.label" class="flex items-end gap-0.5">
                        <span class="text-sm hover:underline!">{{ car.label }}</span>
                        <span class="text-surface-500 text-[11px] font-mono mb-px tracking-tighter">({{ car.value }})</span>
                    </span>
                </ScrollAreaContent>
            </ScrollAreaViewport>
            <ScrollAreaScrollbar orientation="vertical">
                <ScrollAreaHandle />
            </ScrollAreaScrollbar>
        </ScrollArea>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const automobiles = ref([
    { label: 'Audi', value: '200' },
    { label: 'BMW', value: '350' },
    { label: 'Mercedes-Benz', value: '420' },
    { label: 'Volkswagen', value: '510' },
    { label: 'Toyota', value: '610' },
    { label: 'Honda', value: '280' },
    { label: 'Hyundai', value: '390' },
    { label: 'Kia', value: '260' },
    { label: 'Ford', value: '470' },
    { label: 'Renault', value: '530' },
    { label: 'Peugeot', value: '410' },
    { label: 'Citroen', value: '190' },
    { label: 'Skoda', value: '360' },
    { label: 'Seat', value: '210' },
    { label: 'Opel', value: '440' },
    { label: 'Fiat', value: '620' },
    { label: 'Dacia', value: '380' },
    { label: 'Volvo', value: '140' },
    { label: 'Mazda', value: '120' },
    { label: 'Mitsubishi', value: '110' },
    { label: 'Nissan', value: '330' },
    { label: 'Subaru', value: '60' },
    { label: 'Suzuki', value: '170' },
    { label: 'Jeep', value: '95' },
    { label: 'Land Rover', value: '80' },
    { label: 'Porsche', value: '75' },
    { label: 'Ferrari', value: '12' },
    { label: 'Lamborghini', value: '9' },
    { label: 'Bentley', value: '15' },
    { label: 'Rolls-Royce', value: '6' },
    { label: 'Mini', value: '130' },
    { label: 'Tesla', value: '220' },
    { label: 'BYD', value: '55' },
    { label: 'Chery', value: '160' },
    { label: 'MG', value: '145' },
    { label: 'DS Automobiles', value: '40' },
    { label: 'Alfa Romeo', value: '50' },
    { label: 'Lancia', value: '8' },
    { label: 'Cadillac', value: '22' },
    { label: 'Chevrolet', value: '105' },
    { label: 'Dodge', value: '18' },
    { label: 'GMC', value: '14' },
    { label: 'Infiniti', value: '11' },
    { label: 'Acura', value: '7' },
    { label: 'Genesis', value: '35' },
    { label: 'Geely', value: '27' },
    { label: 'Proton', value: '19' },
    { label: 'Togg', value: '65' },
    { label: 'Rivian', value: '4' },
    { label: 'Lucid', value: '3' }
]);
<\/script>
```

## Horizontal

ScrollArea supports horizontal scrolling for content that extends beyond the horizontal viewport.

```vue
<template>
    <div>
        <div class="flex justify-center">
            <ScrollArea class="max-w-md mx-auto">
                <ScrollAreaViewport class="p-3.5!">
                    <ScrollAreaContent>
                        <div class="flex gap-4 min-w-max">
                            <figure v-for="(image, index) in images" :key="index" class="shrink-0">
                                <img :src="image.itemImageSrc" :alt="image.title" class="w-72 h-40 object-cover rounded-sm" />
                                <figcaption class="mt-2 text-xs">
                                    <span class="opacity-60">Photo by</span> <span class="font-medium">{{ image.title }}</span>
                                </figcaption>
                            </figure>
                        </div>
                    </ScrollAreaContent>
                </ScrollAreaViewport>
                <ScrollAreaScrollbar orientation="horizontal">
                    <ScrollAreaHandle />
                </ScrollAreaScrollbar>
            </ScrollArea>
        </div>
    </div>
</template>

<script setup>
import { onMounted, ref } from 'vue';
import { PhotoService } from '@/service/PhotoService';

const images = ref([]);

onMounted(() => {
    PhotoService.getImages().then((data) => (images.value = data));
});
<\/script>
```

## Both Scrollbars

Both vertical and horizontal scrollbars are displayed when the content overflows in both directions.

```vue
<template>
    <div>
        <ScrollArea class="h-80 max-w-sm mx-auto w-full rounded-md overflow-hidden">
            <ScrollAreaViewport class="p-0!">
                <ScrollAreaContent>
                    <table class="min-w-xl w-full text-sm border-collapse border-0">
                        <thead class="sticky top-0 z-10">
                            <tr class="bg-surface-100 dark:bg-surface-800 border-b border-surface">
                                <th v-for="col in columns" :key="col.key" class="border-b border-surface px-4 py-2 text-left text-sm whitespace-nowrap uppercase font-mono font-light">
                                    {{ col.label }}
                                </th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="(city, i) in usCities" :key="i" class="last:border-0 border-b border-surface odd:bg-surface-50 dark:odd:bg-surface-900/40 hover:bg-primary/5">
                                <td class="px-4 py-2 font-medium whitespace-nowrap">{{ city.city }}</td>
                                <td class="px-4 py-2 text-surface-500">{{ city.state }}</td>
                                <td class="px-4 py-2 tabular-nums">{{ city.population.toLocaleString() }}</td>
                                <td class="px-4 py-2 tabular-nums">{{ city.area_km2.toLocaleString() }}</td>
                            </tr>
                        </tbody>
                    </table>
                </ScrollAreaContent>
            </ScrollAreaViewport>
            <ScrollAreaScrollbar orientation="vertical" class="m-0! bg-transparent!">
                <ScrollAreaHandle />
            </ScrollAreaScrollbar>
            <ScrollAreaScrollbar orientation="horizontal" class="m-0! bg-transparent!">
                <ScrollAreaHandle />
            </ScrollAreaScrollbar>
            <ScrollAreaCorner />
        </ScrollArea>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const columns = ref([
    { key: 'city', label: 'City' },
    { key: 'state', label: 'State' },
    { key: 'population', label: 'Population' },
    { key: 'area_km2', label: 'Area (km²)' }
]);

const usCities = ref([
    { city: 'New York', state: 'NY', population: 8419600, area_km2: 783.8 },
    { city: 'Los Angeles', state: 'CA', population: 3980400, area_km2: 1214.9 },
    { city: 'Chicago', state: 'IL', population: 2716000, area_km2: 589.6 },
    { city: 'Houston', state: 'TX', population: 2328000, area_km2: 1651.1 },
    { city: 'Phoenix', state: 'AZ', population: 1690000, area_km2: 1340.6 },
    { city: 'Philadelphia', state: 'PA', population: 1584200, area_km2: 369.6 },
    { city: 'San Antonio', state: 'TX', population: 1547200, area_km2: 1194.0 },
    { city: 'San Diego', state: 'CA', population: 1423800, area_km2: 964.5 },
    { city: 'Dallas', state: 'TX', population: 1341100, area_km2: 882.9 },
    { city: 'San Jose', state: 'CA', population: 1035300, area_km2: 469.7 },
    { city: 'Austin', state: 'TX', population: 1010000, area_km2: 704.0 },
    { city: 'Jacksonville', state: 'FL', population: 949600, area_km2: 2265.3 },
    { city: 'Fort Worth', state: 'TX', population: 918900, area_km2: 920.9 },
    { city: 'Columbus', state: 'OH', population: 905700, area_km2: 577.9 },
    { city: 'Charlotte', state: 'NC', population: 885700, area_km2: 771.0 },
    { city: 'San Francisco', state: 'CA', population: 873900, area_km2: 121.4 },
    { city: 'Indianapolis', state: 'IN', population: 876400, area_km2: 953.0 },
    { city: 'Seattle', state: 'WA', population: 737000, area_km2: 217.0 },
    { city: 'Denver', state: 'CO', population: 715500, area_km2: 401.3 },
    { city: 'Washington', state: 'DC', population: 689500, area_km2: 177.0 },
    { city: 'Boston', state: 'MA', population: 675600, area_km2: 232.1 },
    { city: 'El Paso', state: 'TX', population: 678800, area_km2: 663.7 },
    { city: 'Nashville', state: 'TN', population: 689400, area_km2: 1362.2 },
    { city: 'Detroit', state: 'MI', population: 639100, area_km2: 370.0 },
    { city: 'Oklahoma City', state: 'OK', population: 681100, area_km2: 1608.8 }
]);
<\/script>
```

## Scroll Fade

The mask property adds a gradient fade effect at the scroll edges.

```vue
<template>
    <div class="max-w-56 w-full mx-auto">
        <div class="text-surface-500 dark:text-surface-400 font-medium text-sm uppercase font-mono tracking-tight mb-2">Automobiles</div>
        <ScrollArea class="h-72" mask>
            <ScrollAreaViewport>
                <ScrollAreaContent class="space-y-2">
                    <span v-for="car in automobiles" :key="car.label" class="flex items-end gap-0.5">
                        <span class="text-sm hover:underline!">{{ car.label }}</span>
                        <span class="text-surface-500 text-[11px] font-mono mb-px tracking-tighter">({{ car.value }})</span>
                    </span>
                </ScrollAreaContent>
            </ScrollAreaViewport>
            <ScrollAreaScrollbar orientation="vertical">
                <ScrollAreaHandle />
            </ScrollAreaScrollbar>
        </ScrollArea>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const automobiles = ref([
    { label: 'Audi', value: '200' },
    { label: 'BMW', value: '350' },
    { label: 'Mercedes-Benz', value: '420' },
    { label: 'Volkswagen', value: '510' },
    { label: 'Toyota', value: '610' },
    { label: 'Honda', value: '280' },
    { label: 'Hyundai', value: '390' },
    { label: 'Kia', value: '260' },
    { label: 'Ford', value: '470' },
    { label: 'Renault', value: '530' },
    { label: 'Peugeot', value: '410' },
    { label: 'Citroen', value: '190' },
    { label: 'Skoda', value: '360' },
    { label: 'Seat', value: '210' },
    { label: 'Opel', value: '440' },
    { label: 'Fiat', value: '620' },
    { label: 'Dacia', value: '380' },
    { label: 'Volvo', value: '140' },
    { label: 'Mazda', value: '120' },
    { label: 'Mitsubishi', value: '110' },
    { label: 'Nissan', value: '330' },
    { label: 'Subaru', value: '60' },
    { label: 'Suzuki', value: '170' },
    { label: 'Jeep', value: '95' },
    { label: 'Land Rover', value: '80' },
    { label: 'Porsche', value: '75' },
    { label: 'Ferrari', value: '12' },
    { label: 'Lamborghini', value: '9' },
    { label: 'Bentley', value: '15' },
    { label: 'Rolls-Royce', value: '6' },
    { label: 'Mini', value: '130' },
    { label: 'Tesla', value: '220' },
    { label: 'BYD', value: '55' },
    { label: 'Chery', value: '160' },
    { label: 'MG', value: '145' },
    { label: 'DS Automobiles', value: '40' },
    { label: 'Alfa Romeo', value: '50' },
    { label: 'Lancia', value: '8' },
    { label: 'Cadillac', value: '22' },
    { label: 'Chevrolet', value: '105' },
    { label: 'Dodge', value: '18' },
    { label: 'GMC', value: '14' },
    { label: 'Infiniti', value: '11' },
    { label: 'Acura', value: '7' },
    { label: 'Genesis', value: '35' },
    { label: 'Geely', value: '27' },
    { label: 'Proton', value: '19' },
    { label: 'Togg', value: '65' },
    { label: 'Rivian', value: '4' },
    { label: 'Lucid', value: '3' }
]);
<\/script>
```

## Variant

Change the visibility behavior of scrollbars with the variant property.

```vue
<template>
    <div>
        <div class="flex flex-col items-center">
            <div class="flex flex-wrap items-center justify-center gap-0.5">
                <Button v-for="mode in modes" :key="mode" size="small" :severity="variant === mode ? undefined : 'secondary'" :variant="mode === variant ? undefined : 'text'" class="capitalize cursor-pointer" @click="variant = mode">{{ mode }}</Button>
            </div>
            <div class="mt-8 max-w-56 w-full mx-auto">
                <div class="text-surface-500 dark:text-surface-400 font-medium text-sm uppercase font-mono tracking-tight mb-2">Automobiles</div>
                <ScrollArea class="h-72" :variant="variant">
                    <ScrollAreaViewport>
                        <ScrollAreaContent class="space-y-2">
                            <span v-for="car in automobiles" :key="car.label" class="flex items-end gap-0.5">
                                <span class="text-sm hover:underline!">{{ car.label }}</span>
                                <span class="text-surface-500 text-[11px] font-mono mb-px tracking-tighter">({{ car.value }})</span>
                            </span>
                        </ScrollAreaContent>
                    </ScrollAreaViewport>
                    <ScrollAreaScrollbar orientation="vertical">
                        <ScrollAreaHandle />
                    </ScrollAreaScrollbar>
                </ScrollArea>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const variant = ref('auto');
const modes = ref(['auto', 'hover', 'scroll', 'always', 'hidden']);

const automobiles = ref([
    { label: 'Audi', value: '200' },
    { label: 'BMW', value: '350' },
    { label: 'Mercedes-Benz', value: '420' },
    { label: 'Volkswagen', value: '510' },
    { label: 'Toyota', value: '610' },
    { label: 'Honda', value: '280' },
    { label: 'Hyundai', value: '390' },
    { label: 'Kia', value: '260' },
    { label: 'Ford', value: '470' },
    { label: 'Renault', value: '530' },
    { label: 'Peugeot', value: '410' },
    { label: 'Citroen', value: '190' },
    { label: 'Skoda', value: '360' },
    { label: 'Seat', value: '210' },
    { label: 'Opel', value: '440' },
    { label: 'Fiat', value: '620' },
    { label: 'Dacia', value: '380' },
    { label: 'Volvo', value: '140' },
    { label: 'Mazda', value: '120' },
    { label: 'Mitsubishi', value: '110' },
    { label: 'Nissan', value: '330' },
    { label: 'Subaru', value: '60' },
    { label: 'Suzuki', value: '170' },
    { label: 'Jeep', value: '95' },
    { label: 'Land Rover', value: '80' },
    { label: 'Porsche', value: '75' },
    { label: 'Ferrari', value: '12' },
    { label: 'Lamborghini', value: '9' },
    { label: 'Bentley', value: '15' },
    { label: 'Rolls-Royce', value: '6' },
    { label: 'Mini', value: '130' },
    { label: 'Tesla', value: '220' },
    { label: 'BYD', value: '55' },
    { label: 'Chery', value: '160' },
    { label: 'MG', value: '145' },
    { label: 'DS Automobiles', value: '40' },
    { label: 'Alfa Romeo', value: '50' },
    { label: 'Lancia', value: '8' },
    { label: 'Cadillac', value: '22' },
    { label: 'Chevrolet', value: '105' },
    { label: 'Dodge', value: '18' },
    { label: 'GMC', value: '14' },
    { label: 'Infiniti', value: '11' },
    { label: 'Acura', value: '7' },
    { label: 'Genesis', value: '35' },
    { label: 'Geely', value: '27' },
    { label: 'Proton', value: '19' },
    { label: 'Togg', value: '65' },
    { label: 'Rivian', value: '4' },
    { label: 'Lucid', value: '3' }
]);
<\/script>
```

## Custom

Scrollbar and thumb elements can be customized using classes on the sub-components.

```vue
<template>
    <div class="max-w-56 w-full mx-auto">
        <div class="text-surface-500 dark:text-surface-400 font-medium text-sm uppercase font-mono tracking-tight mb-2">Automobiles</div>
        <ScrollArea class="h-72">
            <ScrollAreaViewport>
                <ScrollAreaContent class="space-y-2">
                    <span v-for="car in automobiles" :key="car.label" class="flex items-end gap-0.5">
                        <span class="text-sm hover:underline!">{{ car.label }}</span>
                        <span class="text-surface-500 text-[11px] font-mono mb-px tracking-tighter">({{ car.value }})</span>
                    </span>
                </ScrollAreaContent>
            </ScrollAreaViewport>
            <ScrollAreaScrollbar class="rounded-full! bg-indigo-500/10!">
                <ScrollAreaHandle class="relative bg-transparent! after:content-[''] after:rounded-full after:bg-indigo-500 after:absolute after:inset-0 active:after:scale-y-90 active:after:scale-x-75 after:transition-transform" />
            </ScrollAreaScrollbar>
        </ScrollArea>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const automobiles = ref([
    { label: 'Audi', value: '200' },
    { label: 'BMW', value: '350' },
    { label: 'Mercedes-Benz', value: '420' },
    { label: 'Volkswagen', value: '510' },
    { label: 'Toyota', value: '610' },
    { label: 'Honda', value: '280' },
    { label: 'Hyundai', value: '390' },
    { label: 'Kia', value: '260' },
    { label: 'Ford', value: '470' },
    { label: 'Renault', value: '530' },
    { label: 'Peugeot', value: '410' },
    { label: 'Citroen', value: '190' },
    { label: 'Skoda', value: '360' },
    { label: 'Seat', value: '210' },
    { label: 'Opel', value: '440' },
    { label: 'Fiat', value: '620' },
    { label: 'Dacia', value: '380' },
    { label: 'Volvo', value: '140' },
    { label: 'Mazda', value: '120' },
    { label: 'Mitsubishi', value: '110' },
    { label: 'Nissan', value: '330' },
    { label: 'Subaru', value: '60' },
    { label: 'Suzuki', value: '170' },
    { label: 'Jeep', value: '95' },
    { label: 'Land Rover', value: '80' },
    { label: 'Porsche', value: '75' },
    { label: 'Ferrari', value: '12' },
    { label: 'Lamborghini', value: '9' },
    { label: 'Bentley', value: '15' },
    { label: 'Rolls-Royce', value: '6' },
    { label: 'Mini', value: '130' },
    { label: 'Tesla', value: '220' },
    { label: 'BYD', value: '55' },
    { label: 'Chery', value: '160' },
    { label: 'MG', value: '145' },
    { label: 'DS Automobiles', value: '40' },
    { label: 'Alfa Romeo', value: '50' },
    { label: 'Lancia', value: '8' },
    { label: 'Cadillac', value: '22' },
    { label: 'Chevrolet', value: '105' },
    { label: 'Dodge', value: '18' },
    { label: 'GMC', value: '14' },
    { label: 'Infiniti', value: '11' },
    { label: 'Acura', value: '7' },
    { label: 'Genesis', value: '35' },
    { label: 'Geely', value: '27' },
    { label: 'Proton', value: '19' },
    { label: 'Togg', value: '65' },
    { label: 'Rivian', value: '4' },
    { label: 'Lucid', value: '3' }
]);
<\/script>
```

## Accessibility

Screen Reader ScrollArea hides the native scrollbar visually while leaving the underlying viewport scrollable. The viewport remains keyboard scrollable so assistive technologies can still navigate the content using standard scroll semantics. Keyboard Support Key Function tab Moves focus to interactive content inside the scroll area. arrow keys Scroll the focused viewport in the corresponding direction (native browser behaviour). page up / page down Scroll by one viewport height. home / end Scroll to the start or the end of the viewport.

## Scroll Area API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| variant | ScrollAreaVariant | 'auto' | Visibility behaviour of the scrollbars. |
| mask | boolean | false | When enabled, applies a fade mask to the scrollable content edges. |
| as | string \| Component | 'DIV' | The element or component used to render the root. |
| asChild | boolean | false | When enabled, root element renders without its own DOM; consumer renders via slot using  `a11yAttrs` . |
| tabIndex | number | 0 | Tab index applied to the viewport when content overflows. The viewport is omitted from the tab order when content fits. |
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
| root | ScrollAreaPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-scrollarea | Class name of the root element |
| p-scrollarea-viewport | Class name of the viewport element |
| p-scrollarea-content | Class name of the content element |
| p-scrollarea-scrollbar | Class name of the scrollbar element |
| p-scrollarea-handle-y | Class name of the vertical handle element |
| p-scrollarea-handle-x | Class name of the horizontal handle element |
| p-scrollarea-corner | Class name of the corner element |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| scrollarea.background | --p-scrollarea-background | Background of root |
| scrollarea.border.color | --p-scrollarea-border-color | Border color of root |
| scrollarea.border.radius | --p-scrollarea-border-radius | Border radius of root |
| scrollarea.focus.ring.width | --p-scrollarea-focus-ring-width | Focus ring width of root |
| scrollarea.focus.ring.style | --p-scrollarea-focus-ring-style | Focus ring style of root |
| scrollarea.focus.ring.color | --p-scrollarea-focus-ring-color | Focus ring color of root |
| scrollarea.focus.ring.offset | --p-scrollarea-focus-ring-offset | Focus ring offset of root |
| scrollarea.focus.ring.shadow | --p-scrollarea-focus-ring-shadow | Focus ring shadow of root |
| scrollarea.viewport.padding | --p-scrollarea-viewport-padding | Padding of viewport |
| scrollarea.scrollbar.background | --p-scrollarea-scrollbar-background | Background of scrollbar |
| scrollarea.scrollbar.margin | --p-scrollarea-scrollbar-margin | Margin of scrollbar |
| scrollarea.scrollbar.size | --p-scrollarea-scrollbar-size | Size of scrollbar (track thickness) |
| scrollarea.scrollbar.transition.duration | --p-scrollarea-scrollbar-transition-duration | Transition duration of scrollbar |
| scrollarea.handle.background | --p-scrollarea-handle-background | Background of handle |
| scrollarea.mask.fade.size | --p-scrollarea-mask-fade-size | Fade size of mask gradient |

## Scroll Area Viewport API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| as | string \| Component | 'DIV' | The element or component used to render the root. |
| asChild | boolean | false | When enabled, root element renders without its own DOM; consumer renders via slot using  `a11yAttrs` . |
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
| root | ScrollAreaViewportPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-scrollarea-viewport | Class name of the root element |

## Scroll Area Content API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| as | string \| Component | 'DIV' | The element or component used to render the root. |
| asChild | boolean | false | When enabled, root element renders without its own DOM; consumer renders via slot using  `a11yAttrs` . |
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
| root | ScrollAreaContentPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-scrollarea-content | Class name of the root element |

## Scroll Area Scrollbar API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| orientation | ScrollAreaScrollbarOrientation | 'vertical' | Axis along which the scrollbar tracks its viewport. |
| as | string \| Component | 'DIV' | The element or component used to render the root. |
| asChild | boolean | false | When enabled, root element renders without its own DOM; consumer renders via slot using  `a11yAttrs` . |
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
| root | ScrollAreaScrollbarPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-scrollarea-scrollbar | Class name of the root element |

## Scroll Area Handle API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| as | string \| Component | 'DIV' | The element or component used to render the root. |
| asChild | boolean | false | When enabled, root element renders without its own DOM; consumer renders via slot using  `a11yAttrs` . |
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
| root | ScrollAreaHandlePassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-scrollarea-handle | Class name of the root element |

## Scroll Area Corner API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| as | string \| Component | 'DIV' | The element or component used to render the root. |
| asChild | boolean | false | When enabled, root element renders without its own DOM; consumer renders via slot using  `a11yAttrs` . |
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
| root | ScrollAreaCornerPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-scrollarea-corner | Class name of the root element |
