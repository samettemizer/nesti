# Carousel

Carousel is a content slider featuring various customization options.

## Basic

Composition-based carousel using native scroll-snap with sub-components for root, content, items, navigation, and indicators.

```vue
<template>
    <div class="mt-8 mb-16">
        <Carousel class="max-w-xl mx-auto" align="center">
            <CarouselContent class="h-[240px]">
                <CarouselItem v-for="i in 5" :key="i">
                    <div class="h-full text-5xl font-semibold bg-surface-50 dark:bg-surface-950 text-surface-950 dark:text-surface-0 flex flex-col items-center justify-center gap-6 rounded-xl border border-surface">
                        <span>{{ i }}</span>
                    </div>
                </CarouselItem>
            </CarouselContent>
            <div class="flex mt-4 gap-4">
                <CarouselIndicators />
                <div class="flex items-center justify-end gap-2 flex-1">
                    <CarouselPrev class="w-9 h-9 flex items-center justify-center rounded-full border border-surface bg-surface-0 dark:bg-surface-800 text-surface-500 dark:text-surface-400 hover:opacity-75 cursor-pointer transition-opacity">
                        <ChevronLeft class="text-lg" />
                    </CarouselPrev>
                    <CarouselNext class="w-9 h-9 flex items-center justify-center rounded-full border border-surface bg-surface-0 dark:bg-surface-800 text-surface-500 dark:text-surface-400 hover:opacity-75 cursor-pointer transition-opacity">
                        <ChevronRight class="text-lg" />
                    </CarouselNext>
                </div>
            </div>
        </Carousel>
    </div>
</template>

<script setup>
import ChevronLeft from '@primeicons/vue/chevron-left';
import ChevronRight from '@primeicons/vue/chevron-right';
<\/script>
```

## Alignment

Use align to control snap alignment and slidesPerPage to show partial slides.

```vue
<template>
    <div class="mt-8 mb-16">
        <Carousel class="max-w-xl mx-auto" align="start" :slidesPerPage="1.5">
            <CarouselContent class="h-[240px]">
                <CarouselItem v-for="i in 5" :key="i">
                    <div class="h-full text-5xl font-semibold bg-surface-50 dark:bg-surface-950 text-surface-950 dark:text-surface-0 flex flex-col items-center justify-center gap-6 rounded-xl border border-surface">
                        <span>{{ i }}</span>
                    </div>
                </CarouselItem>
            </CarouselContent>
            <div class="flex mt-4 gap-4">
                <CarouselIndicators />
                <div class="flex items-center justify-end gap-2 flex-1">
                    <CarouselPrev class="w-9 h-9 flex items-center justify-center rounded-full border border-surface bg-surface-0 dark:bg-surface-800 text-surface-500 dark:text-surface-400 hover:opacity-75 cursor-pointer transition-opacity">
                        <ChevronLeft class="text-lg" />
                    </CarouselPrev>
                    <CarouselNext class="w-9 h-9 flex items-center justify-center rounded-full border border-surface bg-surface-0 dark:bg-surface-800 text-surface-500 dark:text-surface-400 hover:opacity-75 cursor-pointer transition-opacity">
                        <ChevronRight class="text-lg" />
                    </CarouselNext>
                </div>
            </div>
        </Carousel>
    </div>
</template>

<script setup>
import ChevronLeft from '@primeicons/vue/chevron-left';
import ChevronRight from '@primeicons/vue/chevron-right';
<\/script>
```

## Orientation

Set orientation to vertical for a vertical carousel layout.

```vue
<template>
    <div class="mt-8 mb-16">
        <Carousel class="max-w-sm mx-auto flex flex-col gap-8 items-center" orientation="vertical" :slidesPerPage="1.3">
            <CarouselPrev class="w-10 h-10 flex items-center justify-center rounded-full border border-surface bg-surface-0 dark:bg-surface-800 text-surface-500 dark:text-surface-400 hover:opacity-75 cursor-pointer transition-opacity">
                <ChevronUp class="text-lg" />
            </CarouselPrev>
            <CarouselContent class="h-[240px] w-full">
                <CarouselItem v-for="i in 5" :key="i">
                    <div class="h-full text-5xl font-semibold bg-surface-50 dark:bg-surface-950 text-surface-950 dark:text-surface-0 flex flex-col items-center justify-center gap-6 rounded-xl border border-surface">
                        <span>{{ i }}</span>
                    </div>
                </CarouselItem>
            </CarouselContent>
            <CarouselNext class="w-10 h-10 flex items-center justify-center rounded-full border border-surface bg-surface-0 dark:bg-surface-800 text-surface-500 dark:text-surface-400 hover:opacity-75 cursor-pointer transition-opacity">
                <ChevronDown class="text-lg" />
            </CarouselNext>
        </Carousel>
    </div>
</template>

<script setup>
import ChevronDown from '@primeicons/vue/chevron-down';
import ChevronUp from '@primeicons/vue/chevron-up';
<\/script>
```

## Loop

Enable continuous looping with the loop property. Use slidesPerPage to show partial slides.

```vue
<template>
    <div class="mt-8 mb-16">
        <Carousel class="max-w-xl mx-auto" align="center" loop :slidesPerPage="1.75">
            <CarouselContent class="h-[240px]">
                <CarouselItem v-for="i in 5" :key="i">
                    <div class="h-full text-5xl font-semibold bg-surface-50 dark:bg-surface-950 text-surface-950 dark:text-surface-0 flex flex-col items-center justify-center gap-6 rounded-xl border border-surface">
                        <span>{{ i }}</span>
                    </div>
                </CarouselItem>
            </CarouselContent>
            <div class="flex mt-4 gap-4">
                <CarouselIndicators />
                <div class="flex items-center justify-end gap-2 flex-1">
                    <CarouselPrev class="w-9 h-9 flex items-center justify-center rounded-full border border-surface bg-surface-0 dark:bg-surface-800 text-surface-500 dark:text-surface-400 hover:opacity-75 cursor-pointer transition-opacity">
                        <ChevronLeft class="text-lg" />
                    </CarouselPrev>
                    <CarouselNext class="w-9 h-9 flex items-center justify-center rounded-full border border-surface bg-surface-0 dark:bg-surface-800 text-surface-500 dark:text-surface-400 hover:opacity-75 cursor-pointer transition-opacity">
                        <ChevronRight class="text-lg" />
                    </CarouselNext>
                </div>
            </div>
        </Carousel>
    </div>
</template>

<script setup>
import ChevronLeft from '@primeicons/vue/chevron-left';
import ChevronRight from '@primeicons/vue/chevron-right';
<\/script>
```

## Variable Size

Enable autoSize to allow items with variable widths.

```vue
<template>
    <div class="mt-8 mb-16">
        <Carousel class="max-w-xl mx-auto" align="center" autoSize>
            <CarouselContent class="h-[140px]">
                <CarouselItem v-for="(width, i) in items" :key="i" :style="{ width }">
                    <div class="h-full text-4xl font-semibold bg-surface-50 dark:bg-surface-950 text-surface-950 dark:text-surface-0 flex flex-col items-center justify-center gap-6 rounded-lg border border-surface">
                        <span>{{ i + 1 }}</span>
                    </div>
                </CarouselItem>
            </CarouselContent>
            <div class="flex mt-4 gap-4">
                <CarouselIndicators />
                <div class="flex items-center justify-end gap-2 flex-1">
                    <CarouselPrev class="w-9 h-9 flex items-center justify-center rounded-full border border-surface bg-surface-0 dark:bg-surface-800 text-surface-500 dark:text-surface-400 hover:opacity-75 cursor-pointer transition-opacity">
                        <ChevronLeft class="text-lg" />
                    </CarouselPrev>
                    <CarouselNext class="w-9 h-9 flex items-center justify-center rounded-full border border-surface bg-surface-0 dark:bg-surface-800 text-surface-500 dark:text-surface-400 hover:opacity-75 cursor-pointer transition-opacity">
                        <ChevronRight class="text-lg" />
                    </CarouselNext>
                </div>
            </div>
        </Carousel>
    </div>
</template>

<script setup>
import { ref } from 'vue';
import ChevronLeft from '@primeicons/vue/chevron-left';
import ChevronRight from '@primeicons/vue/chevron-right';

const items = ref(['120px', '80px', '200px', '160px', '220px', '180px', '280px', '100px']);
<\/script>
```

## Gallery

Two carousels synchronized via slide input to create a gallery with thumbnail navigation.

```vue
<template>
    <div class="mt-8 mb-16">
        <div class="max-w-2xl mx-auto">
            <Carousel :slide="selectedImage" align="center" @update:slide="onSlideChange">
                <CarouselContent class="h-[396px]">
                    <CarouselItem v-for="(src, i) in images" :key="i" class="basis-full!">
                        <img :draggable="false" :src="src" :alt="\`Image \${i + 1}\`" class="h-full w-full object-cover select-none" />
                    </CarouselItem>
                </CarouselContent>
            </Carousel>
            <Carousel class="mt-3" :spacing="8" align="center" :slide="selectedImage">
                <CarouselContent class="h-[90px]">
                    <CarouselItem
                        v-for="(src, i) in images"
                        :key="i"
                        :class="['cursor-pointer basis-1/4! transition-opacity', selectedImage === i ? '' : 'opacity-60 hover:opacity-40']"
                        @click="selectedImage = i"
                    >
                        <img :draggable="false" :src="src" :alt="\`Image \${i + 1}\`" class="h-full w-full object-cover select-none" />
                    </CarouselItem>
                </CarouselContent>
            </Carousel>
        </div>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const selectedImage = ref(0);
const images = ref([
    'https://images.unsplash.com/photo-1589656966895-2f33e7653819?q=80&w=1470&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1518717758536-85ae29035b6d?q=80&w=1470&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1704905832963-37d6f12654b7?q=80&w=1470&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1470130623320-9583a8d06241?q=80&w=2070&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1678841446310-d045487ef299?q=80&w=1470&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1497752531616-c3afd9760a11?q=80&w=1470&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1511885663737-eea53f6d6187?q=80&w=1374&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1598439210625-5067c578f3f6?q=80&w=1472&auto=format&fit=crop',
    'https://images.unsplash.com/photo-1638255402906-e838358069ab?q=80&w=1631&auto=format&fit=crop'
]);

const onSlideChange = (e) => {
    selectedImage.value = Number(e ?? 0);
};
<\/script>
```

## Accessibility

Screen Reader Carousel uses region role and since any attribute is passed to the main container element, attributes such as aria-label and aria-roledescription can be used as well. The slides container has aria-live attribute set as "polite" if carousel is not in autoplay mode, otherwise "off" would be the value in autoplay. A slide has a group role with an aria-label that refers to the aria.slideNumber property of the locale API. Similarly aria.slide is used as the aria-roledescription of the item. Inactive slides are hidden from the readers with aria-hidden . Next and Previous navigators are button elements with aria-label attributes referring to the aria.nextPageLabel and aria.firstPageLabel properties of the locale API by default respectively, you may still use your own aria roles and attributes as any valid attribute is passed to the button elements implicitly by using nextButtonProps and prevButtonProps . Quick navigation elements are button elements with an aria-label attribute referring to the aria.pageLabel of the locale API. Current page is marked with aria-current . Next/Prev Keyboard Support Key Function tab Moves focus through interactive elements in the carousel. enter Activates navigation. space Activates navigation. Quick Navigation Keyboard Support Key Function tab Moves focus through the active slide link. enter Activates the focused slide link. space Activates the focused slide link. right arrow Moves focus to the next slide link. left arrow Moves focus to the previous slide link. home Moves focus to the first slide link. end Moves focus to the last slide link.

## Carousel API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| value | any | - | An array of objects to display. |
| page | null \| number | null | Page index. Pass with  `v-model:page`  to keep page state in the parent (controlled mode). Provide a static value (e.g.  `:page="2"` ) to set the initial page in uncontrolled mode. Leave unset to start at page 0. |
| numVisible | number | 1 | Number of items per page. |
| numScroll | number | 1 | Number of items to scroll. |
| responsiveOptions | CarouselResponsiveOptions[] | - | An array of options for responsive design. |
| orientation | "horizontal" \| "vertical" | horizontal | Specifies the layout of the component, valid values are 'horizontal' and 'vertical'. |
| verticalViewPortHeight | string | 300px | Height of the viewport in vertical layout. |
| containerClass | any | - | Style class of the viewport container. |
| contentClass | any | - | Style class of main content. |
| indicatorsContentClass | any | - | Style class of the indicator items. |
| circular | boolean | false | Defines if scrolling would be infinite. |
| autoplayInterval | number | 0 | Time in milliseconds to scroll items automatically. |
| showNavigators | boolean | true | Whether to display navigation buttons in container. |
| showIndicators | boolean | true | Whether to display indicator container. |
| prevButtonProps | object | - | Used to pass attributes to the previous Button component. |
| nextButtonProps | object | - | Used to pass attributes to the next Button component. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |
| as | string \| Component | DIV | Use to change the HTML tag of root element. |
| align | "start" \| "center" \| "end" | 'start' | Scroll-snap alignment of each slide within the viewport. |
| loop | boolean | false | Whether the carousel wraps around at the ends. |
| snapType | "mandatory" \| "proximity" | 'mandatory' | Strictness of scroll-snap points. |
| spacing | number | 16 | Gap between slides in pixels. |
| autoSize | boolean | false | When true, items render at their intrinsic width instead of a fixed page fraction. |
| slidesPerPage | number | 1 | Number of slides visible per page. |
| slide | number | - | Controlled zero-based slide index; when set, the carousel scrolls to the slide with this index. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | CarouselPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| header | CarouselPassThroughOptionType | Used to pass attributes to the header's DOM element. |
| contentContainer | CarouselPassThroughOptionType | Used to pass attributes to the content container's DOM element. |
| content | CarouselPassThroughOptionType | Used to pass attributes to the content's DOM element. |
| pcPrevButton | any | Used to pass attributes to the previous button's DOM element. |
| viewport | CarouselPassThroughOptionType | Used to pass attributes to the viewport's DOM element. |
| itemList | CarouselPassThroughOptionType | Used to pass attributes to the items list's DOM element. |
| itemClone | CarouselPassThroughOptionType | Used to pass attributes to the item clone's DOM element. |
| item | CarouselPassThroughOptionType | Used to pass attributes to the item's DOM element. |
| pcNextButton | any | Used to pass attributes to the next button's DOM element. |
| indicatorList | CarouselPassThroughOptionType | Used to pass attributes to the indicator list's DOM element. |
| indicator | CarouselPassThroughOptionType | Used to pass attributes to the indicator's DOM element. |
| indicatorButton | CarouselPassThroughOptionType | Used to pass attributes to the indicator button's DOM element. |
| footer | CarouselPassThroughOptionType | Used to pass attributes to the footer's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-carousel | Class name of the root element |
| p-carousel-header | Class name of the header element |
| p-carousel-content-container | Class name of the content container element |
| p-carousel-content | Class name of the content element |
| p-carousel-prev-button | Class name of the previous button element |
| p-carousel-viewport | Class name of the viewport element |
| p-carousel-item-list | Class name of the item list element |
| p-carousel-item-clone | Class name of the item clone element |
| p-carousel-item | Class name of the item element |
| p-carousel-next-button | Class name of the next button element |
| p-carousel-indicator-list | Class name of the indicator list element |
| p-carousel-indicator | Class name of the indicator element |
| p-carousel-indicator-button | Class name of the indicator button element |
| p-carousel-footer | Class name of the footer element |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| carousel.transition.duration | --p-carousel-transition-duration | Transition duration of root |
| carousel.content.gap | --p-carousel-content-gap | Gap of content |
| carousel.indicator.list.padding | --p-carousel-indicator-list-padding | Padding of indicator list |
| carousel.indicator.list.gap | --p-carousel-indicator-list-gap | Gap of indicator list |
| carousel.indicator.width | --p-carousel-indicator-width | Width of indicator |
| carousel.indicator.height | --p-carousel-indicator-height | Height of indicator |
| carousel.indicator.border.radius | --p-carousel-indicator-border-radius | Border radius of indicator |
| carousel.indicator.focus.ring.width | --p-carousel-indicator-focus-ring-width | Focus ring width of indicator |
| carousel.indicator.focus.ring.style | --p-carousel-indicator-focus-ring-style | Focus ring style of indicator |
| carousel.indicator.focus.ring.color | --p-carousel-indicator-focus-ring-color | Focus ring color of indicator |
| carousel.indicator.focus.ring.offset | --p-carousel-indicator-focus-ring-offset | Focus ring offset of indicator |
| carousel.indicator.focus.ring.shadow | --p-carousel-indicator-focus-ring-shadow | Focus ring shadow of indicator |
| carousel.indicator.background | --p-carousel-indicator-background | Background of indicator |
| carousel.indicator.hover.background | --p-carousel-indicator-hover-background | Hover background of indicator |
| carousel.indicator.active.background | --p-carousel-indicator-active-background | Active background of indicator |

## Carousel Content API

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
| root | CarouselContentPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-carouselcontent | Class name of the root element |

## Carousel Item API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| as | string \| Component | DIV | Use to change the HTML tag of root element. |
| asChild | boolean | false | When enabled, it changes the default rendered element for the one passed as a child element. |
| value | string \| number | - | Unique identifier for the item, exposed as  `data-value`  on the root element. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | CarouselItemPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-carousel-item | Class name of the root element |

## Carousel Indicators API

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
| root | CarouselIndicatorsPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-carousel-indicator-list | Class name of the root element |

## Carousel Indicator API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| as | string \| Component | BUTTON | Use to change the HTML tag of root element. |
| asChild | boolean | false | When enabled, it changes the default rendered element for the one passed as a child element. |
| page | number | - | Zero-based page index this indicator represents. Clicking the indicator scrolls the carousel to this page. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | CarouselIndicatorPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-carousel-indicator | Class name of the root element |

## Carousel Next API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| as | string \| Component | BUTTON | Use to change the HTML tag of root element. |
| asChild | boolean | false | When enabled, it changes the default rendered element for the one passed as a child element. |
| disabled | boolean | false | When present, it specifies that the element should be disabled. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | CarouselNextPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-carousel-next | Class name of the root element |

## Carousel Prev API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| as | string \| Component | BUTTON | Use to change the HTML tag of root element. |
| asChild | boolean | false | When enabled, it changes the default rendered element for the one passed as a child element. |
| disabled | boolean | false | When present, it specifies that the element should be disabled. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | CarouselPrevPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-carousel-prev | Class name of the root element |
