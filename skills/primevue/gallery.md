# Gallery

Gallery is an image viewer with zoom, rotate, flip and download capabilities.

## Basic

Displays a collection of images with a lightbox viewer.

```vue
<template>
    <Gallery class="w-full not-data-fullscreen:h-150!">
        <GalleryBackdrop />

        <GalleryPrev>
            <ChevronLeft />
        </GalleryPrev>
        <GalleryNext>
            <ChevronRight />
        </GalleryNext>

        <GalleryContent>
            <GalleryItem v-for="(image, index) in images" :key="image">
                <img :src="image" :alt="\`image-\${index + 1}\`" />
            </GalleryItem>
        </GalleryContent>
    </Gallery>
</template>

<script setup>
import ChevronLeft from '@primeicons/vue/chevron-left';
import ChevronRight from '@primeicons/vue/chevron-right';

const photos = [
    [10, 1200, 800],
    [11, 800, 1200],
    [15, 1400, 700],
    [16, 700, 1050],
    [17, 1000, 1000]
];

const images = photos.map(([id, w, h]) => \`https://picsum.photos/id/\${id}/\${w}/\${h}\`);
<\/script>
```

## Toolbar

Add a GalleryHeader with action sub-components like GalleryRotateLeft , GalleryZoomIn , GalleryDownload , and GalleryFullScreen to expose image controls.

```vue
<template>
    <Gallery class="h-150!">
        <GalleryBackdrop />

        <GalleryPrev>
            <ChevronLeft />
        </GalleryPrev>
        <GalleryNext>
            <ChevronRight />
        </GalleryNext>

        <GalleryHeader class="justify-end gap-0.5">
            <GalleryRotateLeft>
                <Replay />
            </GalleryRotateLeft>
            <GalleryRotateRight>
                <Refresh />
            </GalleryRotateRight>
            <GalleryZoomIn>
                <SearchPlus />
            </GalleryZoomIn>
            <GalleryZoomOut>
                <SearchMinus />
            </GalleryZoomOut>
            <GalleryFlipX>
                <ArrowsH />
            </GalleryFlipX>
            <GalleryFlipY>
                <ArrowsV />
            </GalleryFlipY>
            <GalleryDownload>
                <Download />
            </GalleryDownload>
            <GalleryFullScreen class="group">
                <ArrowUpRightAndArrowDownLeftFromCenter class="group-data-[fullscreen]:hidden" />
                <ArrowDownLeftAndArrowUpRightToCenter class="hidden group-data-[fullscreen]:block" />
            </GalleryFullScreen>
        </GalleryHeader>

        <GalleryContent>
            <GalleryItem v-for="(image, index) in images" :key="image">
                <img :src="image" :alt="\`image-\${index + 1}\`" />
            </GalleryItem>
        </GalleryContent>
    </Gallery>
</template>

<script setup>
import ArrowDownLeftAndArrowUpRightToCenter from '@primeicons/vue/arrow-down-left-and-arrow-up-right-to-center';
import ArrowUpRightAndArrowDownLeftFromCenter from '@primeicons/vue/arrow-up-right-and-arrow-down-left-from-center';
import ArrowsH from '@primeicons/vue/arrows-h';
import ArrowsV from '@primeicons/vue/arrows-v';
import ChevronLeft from '@primeicons/vue/chevron-left';
import ChevronRight from '@primeicons/vue/chevron-right';
import Download from '@primeicons/vue/download';
import Refresh from '@primeicons/vue/refresh';
import Replay from '@primeicons/vue/replay';
import SearchMinus from '@primeicons/vue/search-minus';
import SearchPlus from '@primeicons/vue/search-plus';

const photos = [
    [10, 1200, 800],
    [11, 800, 1200],
    [15, 1400, 700],
    [16, 700, 1050],
    [17, 1000, 1000]
];

const images = photos.map(([id, w, h]) => \`https://picsum.photos/id/\${id}/\${w}/\${h}\`);
<\/script>
```

## Thumbnails

Add a GalleryFooter with GalleryThumbnail to render a thumbnail strip for quick navigation.

```vue
<template>
    <Gallery class="h-150!">
        <GalleryBackdrop />

        <GalleryPrev>
            <ChevronLeft />
        </GalleryPrev>
        <GalleryNext>
            <ChevronRight />
        </GalleryNext>

        <GalleryContent>
            <GalleryItem v-for="(image, index) in images" :key="image">
                <img :src="image" :alt="\`image-\${index + 1}\`" />
            </GalleryItem>
        </GalleryContent>

        <GalleryFooter>
            <GalleryThumbnail>
                <GalleryThumbnailContent>
                    <GalleryThumbnailItem v-for="(image, index) in images" :key="index" :index="index">
                        <img draggable="false" :src="image" class="h-full w-full object-cover" />
                    </GalleryThumbnailItem>
                </GalleryThumbnailContent>
            </GalleryThumbnail>
        </GalleryFooter>
    </Gallery>
</template>

<script setup>
import ChevronLeft from '@primeicons/vue/chevron-left';
import ChevronRight from '@primeicons/vue/chevron-right';

const photos = [
    [10, 1200, 800],
    [11, 800, 1200],
    [15, 1400, 700],
    [16, 700, 1050],
    [17, 1000, 1000],
    [18, 1300, 650],
    [19, 600, 1200],
    [20, 1200, 900],
    [27, 750, 1125],
    [28, 1400, 800],
    [29, 800, 1100],
    [36, 1100, 700],
    [37, 650, 1300],
    [39, 1200, 750],
    [42, 900, 1200],
    [43, 1300, 800],
    [47, 700, 1400],
    [48, 1000, 800],
    [49, 800, 1000],
    [50, 1400, 600],
    [52, 600, 900],
    [53, 1200, 1200],
    [54, 900, 600],
    [55, 750, 1000],
    [56, 1100, 800],
    [57, 1400, 900],
    [58, 850, 1275],
    [59, 1000, 600],
    [60, 600, 1000],
    [64, 1300, 1300]
];

const images = photos.map(([id, w, h]) => \`https://picsum.photos/id/\${id}/\${w}/\${h}\`);
<\/script>
```

## Single

Click on the image to open it in a fullscreen dialog without thumbnails or navigation buttons.

```vue
<template>
    <div class="flex justify-center">
        <div class="w-80 aspect-3/2 cursor-pointer hover:opacity-75 transition-opacity" @click="open = true">
            <img :src="image" alt="image" class="w-full h-full object-cover rounded-lg" />
        </div>
        <Gallery v-if="open" fullscreen @update:fullscreen="open = $event">
            <GalleryBackdrop />
            <GalleryHeader class="justify-end gap-0.5">
                <GalleryRotateLeft>
                    <Replay />
                </GalleryRotateLeft>
                <GalleryRotateRight>
                    <Refresh />
                </GalleryRotateRight>
                <GalleryZoomIn>
                    <SearchPlus />
                </GalleryZoomIn>
                <GalleryZoomOut>
                    <SearchMinus />
                </GalleryZoomOut>
                <GalleryFlipX>
                    <ArrowsH />
                </GalleryFlipX>
                <GalleryFlipY>
                    <ArrowsV />
                </GalleryFlipY>
                <GalleryDownload>
                    <Download />
                </GalleryDownload>
                <button class="p-gallery-action" @click="open = false">
                    <Times />
                </button>
            </GalleryHeader>
            <GalleryContent>
                <GalleryItem>
                    <img :src="image" alt="image" />
                </GalleryItem>
            </GalleryContent>
        </Gallery>
    </div>
</template>

<script setup>
import { ref } from 'vue';
import ArrowsH from '@primeicons/vue/arrows-h';
import ArrowsV from '@primeicons/vue/arrows-v';
import Download from '@primeicons/vue/download';
import Refresh from '@primeicons/vue/refresh';
import Replay from '@primeicons/vue/replay';
import SearchMinus from '@primeicons/vue/search-minus';
import SearchPlus from '@primeicons/vue/search-plus';
import Times from '@primeicons/vue/times';

const image = ref('https://picsum.photos/id/10/1200/800');
const open = ref(false);
<\/script>
```

## Grid

Gallery can be used as a lightbox by combining it with a grid of thumbnails. Click on an image to open the gallery in fullscreen mode.

```vue
<template>
    <div class="grid grid-cols-2 md:grid-cols-4 2xl:grid-cols-6 gap-2">
        <div v-for="(image, index) in images" :key="image" class="aspect-square cursor-pointer hover:opacity-75 transition-opacity" @click="openAt(index)">
            <img :src="image" alt="image" class="w-full h-full object-cover rounded-lg" />
        </div>
    </div>

    <Gallery v-if="open" fullscreen v-model:activeIndex="activeIndex" class="transition-opacity duration-200" :class="visible ? 'opacity-100' : 'opacity-0'" @update:fullscreen="onFullscreenChange">
        <GalleryBackdrop />
        <GalleryPrev>
            <ChevronLeft />
        </GalleryPrev>
        <GalleryNext>
            <ChevronRight />
        </GalleryNext>
        <GalleryHeader class="justify-end gap-0.5">
            <GalleryRotateLeft>
                <Replay />
            </GalleryRotateLeft>
            <GalleryRotateRight>
                <Refresh />
            </GalleryRotateRight>
            <GalleryZoomIn>
                <SearchPlus />
            </GalleryZoomIn>
            <GalleryZoomOut>
                <SearchMinus />
            </GalleryZoomOut>
            <GalleryFlipX>
                <ArrowsH />
            </GalleryFlipX>
            <GalleryFlipY>
                <ArrowsV />
            </GalleryFlipY>
            <GalleryDownload>
                <Download />
            </GalleryDownload>
            <button type="button" class="p-gallery-action" @click="close">
                <Times />
            </button>
        </GalleryHeader>
        <GalleryContent>
            <GalleryItem v-for="(image, index) in images" :key="image">
                <img :src="image" :alt="\`image-\${index + 1}\`" class="transition-[scale,filter] duration-300" :class="visible ? 'scale-100 blur-none' : 'scale-[0.9] blur-2xl'" />
            </GalleryItem>
        </GalleryContent>
        <GalleryFooter>
            <GalleryThumbnail>
                <GalleryThumbnailContent>
                    <GalleryThumbnailItem v-for="(image, index) in images" :key="index" :index="index">
                        <img draggable="false" :src="image" class="h-full w-full object-cover" />
                    </GalleryThumbnailItem>
                </GalleryThumbnailContent>
            </GalleryThumbnail>
        </GalleryFooter>
    </Gallery>
</template>

<script setup>
import { nextTick, ref } from 'vue';
import ArrowsH from '@primeicons/vue/arrows-h';
import ArrowsV from '@primeicons/vue/arrows-v';
import ChevronLeft from '@primeicons/vue/chevron-left';
import ChevronRight from '@primeicons/vue/chevron-right';
import Download from '@primeicons/vue/download';
import Refresh from '@primeicons/vue/refresh';
import Replay from '@primeicons/vue/replay';
import SearchMinus from '@primeicons/vue/search-minus';
import SearchPlus from '@primeicons/vue/search-plus';
import Times from '@primeicons/vue/times';

const photos = [
    [10, 1200, 800],
    [11, 800, 1200],
    [15, 1400, 700],
    [16, 700, 1050],
    [17, 1000, 1000],
    [18, 1300, 650],
    [19, 600, 1200],
    [20, 1200, 900],
    [27, 750, 1125],
    [28, 1400, 800],
    [29, 800, 1100],
    [36, 1100, 700],
    [37, 650, 1300],
    [39, 1200, 750],
    [42, 900, 1200],
    [43, 1300, 800],
    [47, 700, 1400],
    [48, 1000, 800],
    [49, 800, 1000],
    [50, 1400, 600],
    [52, 600, 900],
    [53, 1200, 1200],
    [54, 900, 600],
    [55, 750, 1000],
    [56, 1100, 800],
    [57, 1400, 900],
    [58, 850, 1275],
    [59, 1000, 600],
    [60, 600, 1000],
    [64, 1300, 1300]
];

const images = ref(photos.map(([id, w, h]) => \`https://picsum.photos/id/\${id}/\${w}/\${h}\`));
const open = ref(false);
const activeIndex = ref(0);
const visible = ref(false);

const openAt = (index) => {
    activeIndex.value = index;
    open.value = true;
    nextTick(() => requestAnimationFrame(() => (visible.value = true)));
};

const close = () => {
    if (!open.value) return;
    visible.value = false;
    setTimeout(() => (open.value = false), 200);
};

const onFullscreenChange = (value) => {
    if (!value) close();
};
<\/script>
```

## Accessibility

Screen Reader Gallery uses semantic button elements for all interactive controls. Use aria-label attributes on buttons to provide accessible names.

## Gallery API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| activeIndex | number | 0 | Index of the active item. Pair with  `v-model:activeIndex`  for two-way binding. |
| as | string \| Component | DIV | Use to change the HTML tag of root element. |
| asChild | boolean | false | When enabled, it changes the default rendered element for the one passed as a child element. |
| fullscreen | boolean | false | When enabled, the gallery is displayed in fullscreen mode. Pair with  `v-model:fullscreen`  for two-way binding. |
| closeOnEscape | boolean | true | Whether pressing the Escape key exits fullscreen mode. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | GalleryPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-gallery | Class name of the root element |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| gallery.backdrop.background | --p-gallery-backdrop-background | Background of backdrop |
| gallery.header.padding | --p-gallery-header-padding | Padding of header |
| gallery.header.background | --p-gallery-header-background | Background of header |
| gallery.footer.padding | --p-gallery-footer-padding | Padding of footer |
| gallery.footer.background | --p-gallery-footer-background | Background of footer |
| gallery.footer.border.color | --p-gallery-footer-border-color | Border color of footer |
| gallery.item.transition.duration | --p-gallery-item-transition-duration | Transition duration of item (transform and opacity) |
| gallery.action.size | --p-gallery-action-size | Size of action (shared by action / next / prev) |
| gallery.action.border.radius | --p-gallery-action-border-radius | Border radius of action |
| gallery.action.color | --p-gallery-action-color | Color of action |
| gallery.action.hover.background | --p-gallery-action-hover-background | Hover background of action |
| gallery.action.hover.color | --p-gallery-action-hover-color | Hover color of action |
| gallery.action.disabled.opacity | --p-gallery-action-disabled-opacity | Disabled opacity of action |
| gallery.action.transition.duration | --p-gallery-action-transition-duration | Transition duration of action |
| gallery.action.icon.size | --p-gallery-action-icon-size | Icon size of action |
| gallery.navigation.background | --p-gallery-navigation-background | Background of navigation (next / prev) |
| gallery.navigation.size | --p-gallery-navigation-size | Size of navigation |
| gallery.navigation.border.radius | --p-gallery-navigation-border-radius | Border radius of navigation |
| gallery.navigation.color | --p-gallery-navigation-color | Color of navigation |
| gallery.navigation.hover.background | --p-gallery-navigation-hover-background | Hover background of navigation |
| gallery.navigation.hover.color | --p-gallery-navigation-hover-color | Hover color of navigation |
| gallery.navigation.offset | --p-gallery-navigation-offset | Edge offset of navigation |
| gallery.navigation.transition.duration | --p-gallery-navigation-transition-duration | Transition duration of navigation |
| gallery.navigation.icon.size | --p-gallery-navigation-icon-size | Icon size of navigation |
| gallery.thumbnail.size | --p-gallery-thumbnail-size | Size of thumbnail item |
| gallery.thumbnail.padding | --p-gallery-thumbnail-padding | Padding of thumbnail item |
| gallery.thumbnail.background | --p-gallery-thumbnail-background | Background of thumbnail item |
| gallery.thumbnail.border.radius | --p-gallery-thumbnail-border-radius | Border radius of thumbnail item |
| gallery.thumbnail.border.width | --p-gallery-thumbnail-border-width | Border width of thumbnail item (outline width) |
| gallery.thumbnail.hover.border.color | --p-gallery-thumbnail-hover-border-color | Hover border color of thumbnail item |
| gallery.thumbnail.active.border.color | --p-gallery-thumbnail-active-border-color | Active border color of thumbnail item |
| gallery.thumbnail.active.scale | --p-gallery-thumbnail-active-scale | Active scale of thumbnail item |
| gallery.thumbnail.transition.duration | --p-gallery-thumbnail-transition-duration | Transition duration of thumbnail item |
| gallery.thumbnail.content.padding | --p-gallery-thumbnail-content-padding | Padding of thumbnail content |

## Gallery Backdrop API

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
| root | GalleryBackdropPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-gallery-backdrop | Class name of the root element |

## Gallery Header API

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
| root | GalleryHeaderPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-gallery-header | Class name of the root element |

## Gallery Content API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| as | string \| Component | DIV | Use to change the HTML tag of root element. |
| asChild | boolean | false | When enabled, it changes the default rendered element for the one passed as a child element. The slot receives  `a11yAttrs`  that include the function ref Gallery uses as the reference box for item sizing. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | GalleryContentPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-gallery-content | Class name of the root element |

## Gallery Item API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| normalScale | number | 1 | Scale factor when the item is at its natural (non-zoomed) state. |
| zoomedScale | number | 3 | Maximum scale factor reached when the item is zoomed in. |
| as | string \| Component | DIV | Use to change the HTML tag of root element. |
| asChild | boolean | false | When enabled, it changes the default rendered element for the one passed as a child element. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | GalleryItemPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-gallery-item | Class name of the root element |

## Gallery Footer API

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
| root | GalleryFooterPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-gallery-footer | Class name of the root element |

## Gallery Thumbnail API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| as | string \| Component | Carousel | Use to change the rendered element. Defaults to  `Carousel`  to wire the thumbnail strip into the scroll-snap carousel infrastructure. |
| asChild | boolean | false | When enabled, it changes the default rendered element for the one passed as a child element. |
| autoSize | boolean | true | Forwarded to the underlying carousel. Each item sizes itself to its intrinsic content rather than a fixed slide width. |
| loop | boolean | true | Forwarded to the underlying carousel. Whether scrolling wraps around at the ends. |
| align | "start" \| "center" \| "end" | 'center' | Forwarded to the underlying carousel. Snap alignment for each item. |
| spacing | number | 8 | Forwarded to the underlying carousel. Spacing in pixels between items. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | GalleryThumbnailPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-gallery-thumbnail | Class name of the root element |

## Gallery Thumbnail Content API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| as | string \| Component | CarouselContent | Use to change the rendered element. Defaults to  `CarouselContent`  to inherit the scroll-snap track. |
| asChild | boolean | false | When enabled, it changes the default rendered element for the one passed as a child element. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | GalleryThumbnailContentPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-gallery-thumbnail-content | Class name of the root element |

## Gallery Thumbnail Item API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| index | number | undefined | Index of the gallery item this thumbnail represents. When the user clicks it, Gallery sets its  `activeIndex`  to this value. |
| as | string \| Component | CarouselItem | Use to change the rendered element. Defaults to  `CarouselItem`  so the thumbnail participates in the scroll-snap layout provided by the parent carousel. |
| asChild | boolean | false | When enabled, it changes the default rendered element for the one passed as a child element. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | GalleryThumbnailItemPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-gallery-thumbnail-item | Class name of the root element |

## Gallery Prev API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| as | string \| Component | BUTTON | Use to change the HTML tag of root element. |
| asChild | boolean | false | When enabled, it changes the default rendered element for the one passed as a child element. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | GalleryPrevPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-gallery-prev | Class name of the root element |

## Gallery Next API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| as | string \| Component | BUTTON | Use to change the HTML tag of root element. |
| asChild | boolean | false | When enabled, it changes the default rendered element for the one passed as a child element. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | GalleryNextPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-gallery-next | Class name of the root element |

## Gallery Rotate Left API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| as | string \| Component | BUTTON | Use to change the HTML tag of root element. |
| asChild | boolean | false | When enabled, it changes the default rendered element for the one passed as a child element. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | GalleryRotateLeftPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-gallery-rotate-left | Class name of the root element |

## Gallery Rotate Right API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| as | string \| Component | BUTTON | Use to change the HTML tag of root element. |
| asChild | boolean | false | When enabled, it changes the default rendered element for the one passed as a child element. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | GalleryRotateRightPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-gallery-rotate-right | Class name of the root element |

## Gallery Zoom In API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| as | string \| Component | BUTTON | Use to change the HTML tag of root element. |
| asChild | boolean | false | When enabled, it changes the default rendered element for the one passed as a child element. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | GalleryZoomInPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-gallery-zoom-in | Class name of the root element |

## Gallery Zoom Out API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| as | string \| Component | BUTTON | Use to change the HTML tag of root element. |
| asChild | boolean | false | When enabled, it changes the default rendered element for the one passed as a child element. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | GalleryZoomOutPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-gallery-zoom-out | Class name of the root element |

## Gallery Zoom Toggle API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| as | string \| Component | BUTTON | Use to change the HTML tag of root element. |
| asChild | boolean | false | When enabled, it changes the default rendered element for the one passed as a child element. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | GalleryZoomTogglePassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-gallery-zoom-toggle | Class name of the root element |

## Gallery Flip X API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| as | string \| Component | BUTTON | Use to change the HTML tag of root element. |
| asChild | boolean | false | When enabled, it changes the default rendered element for the one passed as a child element. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | GalleryFlipXPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-gallery-flip-x | Class name of the root element |

## Gallery Flip Y API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| as | string \| Component | BUTTON | Use to change the HTML tag of root element. |
| asChild | boolean | false | When enabled, it changes the default rendered element for the one passed as a child element. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | GalleryFlipYPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-gallery-flip-y | Class name of the root element |

## Gallery Download API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| as | string \| Component | BUTTON | Use to change the HTML tag of root element. |
| asChild | boolean | false | When enabled, it changes the default rendered element for the one passed as a child element. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | GalleryDownloadPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-gallery-download | Class name of the root element |

## Gallery Full Screen API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| as | string \| Component | BUTTON | Use to change the HTML tag of root element. |
| asChild | boolean | false | When enabled, it changes the default rendered element for the one passed as a child element. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | GalleryFullScreenPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-gallery-fullscreen | Class name of the root element |
