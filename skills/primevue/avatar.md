# Avatar

Avatar represents people using icons, labels and images.

## Basic

Displays a user representation using an image, icon, or label initials.

```vue
<template>
    <div class="flex items-center justify-center gap-4">
        <Avatar image="https://primefaces.org/cdn/primevue/images/avatar/amyelsner.png" size="large" shape="circle" />
    </div>
</template>

<script setup>
import Avatar from 'primevue/avatar';
<\/script>
```

## Image

Use the image property to display an image as an Avatar.

```vue
<template>
    <div class="flex items-center justify-center gap-4">
        <Avatar image="https://primefaces.org/cdn/primevue/images/avatar/amyelsner.png" size="large" shape="circle" />
        <Avatar image="https://primefaces.org/cdn/primevue/images/avatar/asiyajavayant.png" size="large" shape="circle" />
        <Avatar image="https://primefaces.org/cdn/primevue/images/avatar/onyamalimba.png" size="large" shape="circle" />
    </div>
</template>

<script setup>
import Avatar from 'primevue/avatar';
<\/script>
```

## Badge

A Badge can be used to display a badge on an Avatar.

```vue
<template>
    <div class="flex items-center justify-center gap-8">
        <OverlayBadge value="2" size="small" severity="success">
            <Avatar image="https://primefaces.org/cdn/primevue/images/avatar/onyamalimba.png" size="large" shape="circle" />
        </OverlayBadge>
        <OverlayBadge severity="danger">
            <Avatar image="https://primefaces.org/cdn/primevue/images/organization/walter.jpg" size="large" />
        </OverlayBadge>
    </div>
</template>

<script setup>
import Avatar from 'primevue/avatar';
import OverlayBadge from 'primevue/overlaybadge';
<\/script>
```

## Shape

Avatar comes in two different styles specified with the shape property, square is the default and circle is the alternative.

```vue
<template>
    <div class="flex items-center justify-center gap-4">
        <Avatar image="https://primefaces.org/cdn/primevue/images/organization/walter.jpg" shape="circle" size="large" />
        <Avatar image="https://primefaces.org/cdn/primevue/images/organization/walter.jpg" shape="square" size="large" />
    </div>
</template>

<script setup>
import Avatar from 'primevue/avatar';
<\/script>
```

## Sizes

Use the size property to change the size of an avatar.

```vue
<template>
    <div class="flex flex-col items-center gap-4">
        <div class="flex items-center justify-center gap-4">
            <Avatar image="https://primefaces.org/cdn/primevue/images/avatar/amyelsner.png" shape="circle" />
            <Avatar image="https://primefaces.org/cdn/primevue/images/avatar/amyelsner.png" shape="circle" size="large" />
            <Avatar image="https://primefaces.org/cdn/primevue/images/avatar/amyelsner.png" shape="circle" size="xlarge" />
        </div>
        <div class="flex items-center justify-center gap-4">
            <Avatar label="AB" shape="circle" />
            <Avatar label="AB" shape="circle" size="large" />
            <Avatar label="AB" shape="circle" size="xlarge" />
        </div>
    </div>
</template>

<script setup>
import Avatar from 'primevue/avatar';
<\/script>
```

## AvatarGroup

Grouping is available by wrapping multiple Avatar components inside an AvatarGroup .

```vue
<template>
    <div class="flex justify-center">
        <AvatarGroup>
            <Avatar image="https://primefaces.org/cdn/primevue/images/avatar/amyelsner.png" shape="circle" />
            <Avatar image="https://primefaces.org/cdn/primevue/images/avatar/asiyajavayant.png" shape="circle" />
            <Avatar image="https://primefaces.org/cdn/primevue/images/avatar/onyamalimba.png" shape="circle" />
            <Avatar image="https://primefaces.org/cdn/primevue/images/avatar/ionibowcher.png" shape="circle" />
            <Avatar image="https://primefaces.org/cdn/primevue/images/avatar/xuxuefeng.png" shape="circle" />
            <Avatar label="+2" shape="circle" />
        </AvatarGroup>
    </div>
</template>

<script setup>
import Avatar from 'primevue/avatar';
import AvatarGroup from 'primevue/avatargroup';
<\/script>
```

## Template

Content can easily be customized with the dynamic content instead of using the built-in modes.

```vue
<template>
    <div class="flex justify-center">
        <Avatar size="xlarge">
            <svg width="31" height="33" viewBox="0 0 31 33" fill="none" xmlns="http://www.w3.org/2000/svg" class="block mx-auto">
                <path d="M15.1934 0V0V0L0.0391235 5.38288L2.35052 25.3417L15.1934 32.427V32.427V32.427L28.0364 25.3417L30.3478 5.38288L15.1934 0Z" fill="var(--p-primary-color)" />
                <mask id="mask0_1_52" style="mask-type:luminance" maskUnits="userSpaceOnUse" x="0" y="0" width="31" height="33">
                    <path d="M15.1934 0V0V0L0.0391235 5.38288L2.35052 25.3417L15.1934 32.427V32.427V32.427L28.0364 25.3417L30.3478 5.38288L15.1934 0Z" fill="var(--ground-background)" />
                </mask>
                <g mask="url(#mask0_1_52)">
                    <path fill-rule="evenodd" clip-rule="evenodd" d="M15.1935 0V3.5994V3.58318V20.0075V20.0075V32.427V32.427L28.0364 25.3417L30.3478 5.38288L15.1935 0Z" fill="var(--p-primary-color)" />
                </g>
                <path d="M19.6399 15.3776L18.1861 15.0547L19.3169 16.6695V21.6755L23.1938 18.4458V12.9554L21.4169 13.6013L19.6399 15.3776Z" fill="var(--ground-background)" />
                <path d="M10.5936 15.3776L12.0474 15.0547L10.9166 16.6695V21.6755L7.03966 18.4458V12.9554L8.81661 13.6013L10.5936 15.3776Z" fill="var(--ground-background)" />
                <path
                    fill-rule="evenodd"
                    clip-rule="evenodd"
                    d="M11.3853 16.9726L12.6739 15.0309L13.4793 15.5163H16.7008L17.5061 15.0309L18.7947 16.9726V24.254L17.8283 25.7103L16.7008 26.843H13.4793L12.3518 25.7103L11.3853 24.254V16.9726Z"
                    fill="var(--ground-background)"
                />
                <path d="M19.3168 24.7437L21.4168 22.6444V20.5451L19.3168 22.3214V24.7437Z" fill="var(--ground-background)" />
                <path d="M10.9166 24.7437L8.81662 22.6444V20.5451L10.9166 22.3214V24.7437Z" fill="var(--ground-background)" />
                <path
                    fill-rule="evenodd"
                    clip-rule="evenodd"
                    d="M13.0167 5.68861L11.7244 8.7568L13.8244 14.8932H14.7936V5.68861H13.0167ZM15.4397 5.68861V14.8932H16.5706L18.5091 8.7568L17.2167 5.68861H15.4397Z"
                    fill="var(--ground-background)"
                />
                <path d="M13.8244 14.8932L6.87813 12.3094L5.90888 8.27235L11.8859 8.7568L13.9859 14.8932H13.8244Z" fill="var(--ground-background)" />
                <path d="M16.5706 14.8932L23.5169 12.3094L24.4861 8.27235L18.3476 8.7568L16.4091 14.8932H16.5706Z" fill="var(--ground-background)" />
                <path d="M18.8321 8.27235L22.2245 7.94938L19.9629 5.68861H17.7013L18.8321 8.27235Z" fill="var(--ground-background)" />
                <path d="M11.4013 8.27235L8.00893 7.94938L10.2705 5.68861H12.5321L11.4013 8.27235Z" fill="var(--ground-background)" />
            </svg>
        </Avatar>
    </div>
</template>

<script setup>
import Avatar from 'primevue/avatar';
<\/script>
```

## Accessibility

Screen Reader Avatar does not include any roles and attributes by default. Any attribute is passed to the root element so you may add a role like img along with aria-labelledby or aria-label to describe the component. In case avatars need to be tabbable, tabIndex can be added as well to implement custom key handlers. Keyboard Support Component does not include any interactive elements.

## Avatar API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| label | string | - | Defines the text to display. |
| icon | string | - | Defines the icon to display. |
| image | string | - | Defines the image to display. |
| size | any | normal | Size of the element. |
| shape | any | square | Shape of the element. |
| ariaLabel | string | - | Establishes a string value that labels the component. |
| ariaLabelledby | string | - | Establishes relationships between the component and label(s) where its value should be one or more element IDs. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | AvatarPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| label | AvatarPassThroughOptionType | Used to pass attributes to the label's DOM element. |
| icon | AvatarPassThroughOptionType | Used to pass attributes to the icon's DOM element. |
| image | AvatarPassThroughOptionType | Used to pass attributes to the image's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-avatar | Class name of the root element |
| p-avatar-label | Class name of the label element |
| p-avatar-icon | Class name of the icon element |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| avatar.width | --p-avatar-width | Width of root |
| avatar.height | --p-avatar-height | Height of root |
| avatar.font.weight | --p-avatar-font-weight | Font weight of root |
| avatar.font.size | --p-avatar-font-size | Font size of root |
| avatar.background | --p-avatar-background | Background of root |
| avatar.color | --p-avatar-color | Color of root |
| avatar.border.radius | --p-avatar-border-radius | Border radius of root |
| avatar.icon.size | --p-avatar-icon-size | Size of icon |
| avatar.group.border.color | --p-avatar-group-border-color | Border color of group |
| avatar.group.offset | --p-avatar-group-offset | Offset of group |
| avatar.lg.width | --p-avatar-lg-width | Width of lg |
| avatar.lg.height | --p-avatar-lg-height | Height of lg |
| avatar.lg.font.size | --p-avatar-lg-font-size | Font size of lg |
| avatar.lg.icon.size | --p-avatar-lg-icon-size | Icon size of lg |
| avatar.lg.group.offset | --p-avatar-lg-group-offset | Group offset of lg |
| avatar.xl.width | --p-avatar-xl-width | Width of xl |
| avatar.xl.height | --p-avatar-xl-height | Height of xl |
| avatar.xl.font.size | --p-avatar-xl-font-size | Font size of xl |
| avatar.xl.icon.size | --p-avatar-xl-icon-size | Icon size of xl |
| avatar.xl.group.offset | --p-avatar-xl-group-offset | Group offset of xl |

## Avatar Group API

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
| root | AvatarGroupPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-avatar-group |  |
