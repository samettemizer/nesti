# Divider

Divider is used to separate contents.

## Basic

Divider is placed between items to separate content.

```vue
<template>
    <div class="flex justify-center">
        <div class="max-w-sm w-full text-sm">
            <div class="flex items-center justify-between">
                <span class="text-color font-medium">Subtotal</span>
                <span class="text-color">$89.00</span>
            </div>
            <Divider />
            <div class="flex items-center justify-between">
                <span class="text-color font-medium">Shipping</span>
                <span class="text-color">$5.99</span>
            </div>
            <Divider />
            <div class="flex items-center justify-between">
                <span class="text-color font-semibold">Total</span>
                <span class="text-color font-semibold">$94.99</span>
            </div>
        </div>
    </div>
</template>
```

## Type

Style of the border is configured with the type property that can be solid , dotted or dashed .

```vue
<template>
    <div class="flex justify-center">
        <div class="max-w-md w-full">
            <p class="text-sm">Fast setup, no credit card required</p>
            <Divider type="solid" />
            <p class="text-sm">Cancel anytime from your account</p>
            <Divider type="dotted" />
            <p class="text-sm">24/7 support included</p>
            <Divider type="dashed" />
            <p class="text-sm">No long-term commitments</p>
        </div>
    </div>
</template>
```

## Vertical

Vertical divider is enabled by setting the layout property as vertical .

```vue
<template>
    <div class="flex justify-center">
        <div class="flex w-fit">
            <div>
                <div class="uppercase font-mono text-xs">Invoice No</div>
                <div class="font-light">0000123</div>
            </div>
            <Divider layout="vertical" />
            <div>
                <div class="uppercase font-mono text-xs">Issued</div>
                <div class="font-light">01/01/2026</div>
            </div>
            <Divider layout="vertical" />
            <div>
                <div class="uppercase font-mono text-xs">Due Date</div>
                <div class="font-light">02/02/2026</div>
            </div>
        </div>
    </div>
</template>
```

## Alignment

Children are rendered within the boundaries of the divider where location of the content is configured with the align property. In horizontal layout, alignment options are left , center and right whereas vertical mode supports top , center and bottom .

```vue
<template>
    <div class="flex justify-center">
        <div class="max-w-md w-full">
            <p class="text-sm">Fast setup with a simple onboarding process, no credit card required to get started.</p>
            <Divider align="left" type="solid">
                <code class="uppercase text-xs">Getting started</code>
            </Divider>
            <p class="text-sm">Cancel anytime directly from your account settings, with no questions asked.</p>
            <Divider align="center" type="dotted">
                <code class="uppercase text-xs">Flexibility</code>
            </Divider>
            <p class="text-sm">24/7 support included to help you resolve issues quickly, whenever you need assistance.</p>
            <Divider align="right" type="dashed">
                <code class="uppercase text-xs">Support</code>
            </Divider>
            <p class="text-sm">No long-term commitments or hidden contracts, just transparent and flexible pricing.</p>
        </div>
    </div>
</template>
```

## Accessibility

Screen Reader Divider uses a separator role with aria-orientation set to either "horizontal" or "vertical". Keyboard Support Component does not include any interactive elements.

## Divider API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| align | any | - | Alignment of the content. |
| layout | any | horizontal | Specifies the orientation, valid values are 'horizontal' and 'vertical'. |
| type | any | solid | Border style type. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | DividerPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| content | DividerPassThroughOptionType | Used to pass attributes to the content's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-divider | Class name of the root element |
| p-divider-content | Class name of the content element |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| divider.border.color | --p-divider-border-color | Border color of root |
| divider.content.background | --p-divider-content-background | Background of content |
| divider.content.color | --p-divider-content-color | Color of content |
| divider.horizontal.margin | --p-divider-horizontal-margin | Margin of horizontal |
| divider.horizontal.padding | --p-divider-horizontal-padding | Padding of horizontal |
| divider.horizontal.content.padding | --p-divider-horizontal-content-padding | Content padding of horizontal |
| divider.vertical.margin | --p-divider-vertical-margin | Margin of vertical |
| divider.vertical.padding | --p-divider-vertical-padding | Padding of vertical |
| divider.vertical.content.padding | --p-divider-vertical-content-padding | Content padding of vertical |
