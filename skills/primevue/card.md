# Card

Card is a flexible container component.

## Basic

A container with a header, body, and footer for structured content.

```vue
<template>
    <div class="flex justify-center">
        <Card class="max-w-sm w-full">
            <template #title>Starter Plan</template>
            <template #subtitle>For personal projects</template>
            <template #content>
                <p class="m-0">Includes essential features, basic analytics and access to community support.</p>
            </template>
            <template #footer>
                <span class="text-sm text-surface-500 dark:text-surface-400">Cancel anytime. No credit card required.</span>
            </template>
        </Card>
    </div>
</template>

<script setup>
<\/script>
```

## With Form

Card can be used as a form container with input fields and action buttons.

```vue
<template>
    <div class="flex justify-center">
        <Card class="max-w-sm w-full">
            <template #title>Welcome back</template>
            <template #subtitle>Sign in with your email to continue.</template>
            <template #content>
                <form class="space-y-6 mt-3">
                    <div class="flex flex-col gap-2">
                        <Label for="email">Email</Label>
                        <InputText id="email" v-model="email" type="email" />
                    </div>
                    <div class="flex flex-col gap-2">
                        <div class="flex items-center justify-between">
                            <Label for="password" class="flex-1">Password</Label>
                            <Button variant="link" class="p-0">Forgot password?</Button>
                        </div>
                        <InputText id="password" v-model="password" type="password" />
                    </div>
                </form>
            </template>
            <template #footer>
                <div class="flex flex-col gap-4">
                    <Button class="w-full">Login</Button>
                    <Button severity="secondary" variant="outlined" class="w-full">Login with Google</Button>
                    <div class="mt-2 text-center text-surface-500 text-sm">
                        Don't have an account?
                        <Button variant="link" class="p-0">Sign up</Button>
                    </div>
                </div>
            </template>
        </Card>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const email = ref('');
const password = ref('');
<\/script>
```

## Advanced

Use the header template to place an image, avatar or other content in the header.

```vue
<template>
    <div class="flex justify-center">
        <Card class="max-w-sm w-full overflow-hidden" :pt="{ body: { class: 'pt-16!' } }">
            <template #header>
                <div class="relative">
                    <img
                        class="w-full max-h-42 object-cover"
                        alt="user header"
                        src="https://images.unsplash.com/photo-1513649718256-1a7162666bad?q=80&w=2070&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D"
                    />
                    <Avatar shape="circle" class="w-24! h-24! border-3 border-surface-0 dark:border-surface-900 absolute! -bottom-12! left-4!">
                        <img src="https://images.unsplash.com/photo-1722495178488-c8056c4ec2c0?q=80&w=2081&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D" />
                    </Avatar>
                </div>
            </template>
            <template #title>
                <span class="font-bold text-xl">Sakura Fresh Market</span>
            </template>
            <template #subtitle>
                <div class="flex items-center gap-2">
                    <Tag severity="info" value="Daily" />
                    <Tag severity="info" value="Premium" />
                </div>
            </template>
            <template #content>
                <div class="space-y-4">
                    <p>Sakura Fresh Market is your go-to store for fresh local produce, Japanese snacks, and daily essentials — all in one place!</p>
                    <div class="flex items-center gap-2">
                        <StarFill class="text-yellow-500" />
                        <span><b>4.6</b> (200+ reviews)</span>
                    </div>
                    <div class="flex items-center gap-2">
                        <MapMarker />
                        <span>Tokyo, Shibuya-ku</span>
                    </div>
                </div>
            </template>
            <template #footer>
                <div class="flex items-center gap-2 mt-4">
                    <Button severity="secondary" outlined class="flex-1">
                        <Phone />
                        Call Us
                    </Button>
                    <Button class="flex-1">
                        <Globe />
                        Visit Site
                    </Button>
                </div>
            </template>
        </Card>
    </div>
</template>

<script setup>
import Globe from '@primeicons/vue/globe';
import MapMarker from '@primeicons/vue/map-marker';
import Phone from '@primeicons/vue/phone';
import StarFill from '@primeicons/vue/star-fill';
<\/script>
```

## Accessibility

Screen Reader A card can be utilized in many use cases as a result no role is enforced, in fact a role may not be necessary if the card is used for presentational purposes only. Any valid attribute is passed to the container element so if you require to use one of the landmark roles like region , you may use the role property. Keyboard Support Component does not include any interactive elements.

```vue
<template>
    <Card role="region">
        Content
    </Card>
</template>
```

## Card API

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
| root | CardPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| header | CardPassThroughOptionType | Used to pass attributes to the header's DOM element. |
| body | CardPassThroughOptionType | Used to pass attributes to the body's DOM element. |
| caption | CardPassThroughOptionType | Used to pass attributes to the caption's DOM element. |
| title | CardPassThroughOptionType | Used to pass attributes to the title's DOM element. |
| subtitle | CardPassThroughOptionType | Used to pass attributes to the subtitle's DOM element. |
| content | CardPassThroughOptionType | Used to pass attributes to the content's DOM element. |
| footer | CardPassThroughOptionType | Used to pass attributes to the footer's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-card | Class name of the root element |
| p-card-header | Class name of the header element |
| p-card-body | Class name of the body element |
| p-card-caption | Class name of the caption element |
| p-card-title | Class name of the title element |
| p-card-subtitle | Class name of the subtitle element |
| p-card-content | Class name of the content element |
| p-card-footer | Class name of the footer element |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| card.background | --p-card-background | Background of root |
| card.border.radius | --p-card-border-radius | Border radius of root |
| card.color | --p-card-color | Color of root |
| card.shadow | --p-card-shadow | Shadow of root |
| card.body.padding | --p-card-body-padding | Padding of body |
| card.body.gap | --p-card-body-gap | Gap of body |
| card.caption.gap | --p-card-caption-gap | Gap of caption |
| card.title.font.size | --p-card-title-font-size | Font size of title |
| card.title.font.weight | --p-card-title-font-weight | Font weight of title |
| card.subtitle.color | --p-card-subtitle-color | Color of subtitle |
| card.subtitle.font.size | --p-card-subtitle-font-size | Font size of subtitle |
| card.subtitle.font.weight | --p-card-subtitle-font-weight | Font weight of subtitle |
