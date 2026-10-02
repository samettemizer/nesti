# Icons

@primeicons/vue is the default icon library of PrimeVue with over 300 icons as standalone Vue components developed by PrimeTek. The library is optional as PrimeVue components can use any icon with templating.

## Download

@primeicons/vue is available at npm, run the following command to download it to your project.

```vue
npm install @primeicons/vue
```

## Import

Each icon is a standalone Vue component. Import them individually for optimal tree-shaking, or use the named exports from the package root.

```vue
// Tree-shakeable, per-icon imports (recommended)
import Search from '@primeicons/vue/search';
import User from '@primeicons/vue/user';

// Named imports from the package root
import { Search, User, Check } from '@primeicons/vue';
```

## Figma

PrimeIcons library is now available on Figma Community . By adding them as a library, you can easily use these icons in your designs.

## Basic

Each icon is a standalone Vue component rendered as an inline SVG, displayed by importing it from @primeicons/vue and using it as a tag.

```vue
<template>
    <Check />
    <Times />
    <Search />
    <User />
</template>

<script setup>
import Check from '@primeicons/vue/check';
import Times from '@primeicons/vue/times';
import Search from '@primeicons/vue/search';
import User from '@primeicons/vue/user';
<\/script>
```

## Size

Size of an icon is controlled with the size property that accepts a number in pixels or any CSS length value.

```vue
<template>
    <Check :size="16" />
    <Times :size="24" />
    <Search :size="32" />
    <User :size="40" />
</template>

<script setup>
import Check from '@primeicons/vue/check';
import Times from '@primeicons/vue/times';
import Search from '@primeicons/vue/search';
import User from '@primeicons/vue/user';
<\/script>
```

## Color

Icon color is defined with the color property which is inherited from the parent with currentColor by default.

```vue
<template>
    <Check color="slateblue" />
    <Times color="green" />
    <Search color="var(--p-primary-color)" />
    <User color="#708090" />
</template>

<script setup>
import Check from '@primeicons/vue/check';
import Times from '@primeicons/vue/times';
import Search from '@primeicons/vue/search';
import User from '@primeicons/vue/user';
<\/script>
```

## Spin

Use the spin property to apply a rotation animation to an icon. Alternatively, a spin animation utility such as animate-spin from Tailwind can also be used.

```vue
<template>
    <Spinner spin :size="32" />
    <Cog spin :size="32" />
</template>

<script setup>
import Spinner from '@primeicons/vue/spinner';
import Cog from '@primeicons/vue/cog';
<\/script>
```

## Programmatic

Icon components can be referenced programmatically by passing the component itself to APIs that accept an icon , such as the model of a Menu.

```vue
<template>
    <div class="card flex justify-center">
        <Menu :model="items" />
    </div>
</template>

<script setup>
import { ref } from 'vue';
import Plus from '@primeicons/vue/plus';
import Download from '@primeicons/vue/download';

const items = ref([
    {
        label: 'File',
        items: [
            { label: 'New', icon: Plus },
            { label: 'Open', icon: Download }
        ]
    }
]);
<\/script>
```

## List

Here is the full list of icons available as Vue components. Click any icon to copy its import statement.
