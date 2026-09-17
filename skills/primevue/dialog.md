# Dialog

Dialog is a container to display content in an overlay window.

## Basic

Dialog is used as a container and visibility is controlled with a binding to visible property.

```vue
<template>
    <div class="flex justify-center">
        <Button @click="visible = true">Edit Profile</Button>
        <Dialog v-model:visible="visible" modal header="Edit Profile" :style="{ width: '24rem' }">
            <div class="flex flex-col gap-4">
                <div class="flex flex-col gap-1.5">
                    <Label for="name">Name</Label>
                    <InputText id="name" v-model="name" autoFocus />
                </div>
                <div class="flex flex-col gap-1.5">
                    <Label for="email">Email</Label>
                    <InputText id="email" v-model="email" />
                </div>
            </div>
            <template #footer>
                <Button severity="secondary" variant="outlined" @click="visible = false">Cancel</Button>
                <Button @click="visible = false">Save</Button>
            </template>
        </Dialog>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const visible = ref(false);
const name = ref('Amanda Miller');
const email = ref('amanda@example.com');
<\/script>
```

## Template

Header and Footer sections allow customization via templating.

```vue
<template>
    <div class="flex justify-center">
        <Button @click="visible = true">Show</Button>
        <Dialog v-model:visible="visible" modal :style="{ width: '25rem' }">
            <template #header>
                <div class="inline-flex items-center justify-center gap-2">
                    <Avatar image="https://primefaces.org/cdn/primevue/images/avatar/amyelsner.png" shape="circle" />
                    <span class="font-bold whitespace-nowrap">Amy Elsner</span>
                </div>
            </template>
            <span class="text-surface-500 dark:text-surface-400 block mb-8 text-sm">Update your information.</span>
            <div class="flex items-center gap-4 mb-4">
                <label for="username" class="font-semibold w-24 text-sm">Username</label>
                <InputText id="username" class="flex-auto" autocomplete="off" />
            </div>
            <div class="flex items-center gap-4 mb-2">
                <label for="email" class="font-semibold w-24 text-sm">Email</label>
                <InputText id="email" class="flex-auto" autocomplete="off" />
            </div>
            <template #footer>
                <Button text severity="secondary" @click="visible = false">Cancel</Button>
                <Button variant="outlined" severity="secondary" @click="visible = false">Save</Button>
            </template>
        </Dialog>
    </div>
</template>

<script setup>
import { ref } from "vue";

const visible = ref(false);
<\/script>
```

## Draggable

Enabling the draggable property lets the user reposition the Dialog by dragging it from its header.

```vue
<template>
    <div class="flex justify-center">
        <Button @click="visible = true">Open Note</Button>
        <Dialog v-model:visible="visible" draggable modal header="Quick Note" :style="{ width: '24rem' }">
            <div class="flex flex-col gap-4">
                <p class="text-sm text-surface-500 dark:text-surface-400 mt-0 mb-0">Drag this dialog by its header to reposition it anywhere on the screen.</p>
                <Textarea v-model="note" class="w-full h-32 resize-none" placeholder="Type your note here..." autoFocus />
            </div>
            <template #footer>
                <Button severity="secondary" @click="visible = false">Discard</Button>
                <Button @click="visible = false">Save Note</Button>
            </template>
        </Dialog>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const visible = ref(false);
const note = ref('Remember to review the design specs for the new dashboard layout before the meeting tomorrow.');
<\/script>
```

## Position

The position property is used to display a Dialog at all edges and corners of the screen.

```vue
<template>
    <div>
        <div class="flex flex-wrap justify-center gap-2 mb-2">
            <Button severity="secondary" class="min-w-40" @click="openPosition('left')"> Left </Button>
            <Button severity="secondary" class="min-w-40" @click="openPosition('right')"> Right </Button>
        </div>
        <div class="flex flex-wrap justify-center gap-2 mb-2">
            <Button severity="secondary" class="min-w-40" @click="openPosition('topleft')"> TopLeft </Button>
            <Button severity="secondary" class="min-w-40" @click="openPosition('top')"> Top </Button>
            <Button severity="secondary" class="min-w-40" @click="openPosition('topright')"> TopRight </Button>
        </div>
        <div class="flex flex-wrap justify-center gap-2">
            <Button severity="secondary" class="min-w-40" @click="openPosition('bottomleft')"> BottomLeft </Button>
            <Button severity="secondary" class="min-w-40" @click="openPosition('bottom')"> Bottom </Button>
            <Button severity="secondary" class="min-w-40" @click="openPosition('bottomright')"> BottomRight </Button>
        </div>

        <Dialog v-model:visible="visible" :position="position" modal :draggable="false" header="Edit Profile" :style="{ width: '25rem' }">
            <div class="flex flex-col gap-6">
                <span class="text-surface-500 dark:text-surface-400">Update your information.</span>
                <div class="flex flex-col gap-1">
                    <Label for="username" class="font-semibold">Username</Label>
                    <InputText id="username" v-model="username"  autoFocus/>
                </div>
                <div class="flex flex-col gap-1">
                    <Label for="email" class="font-semibold">Email</Label>
                    <InputText id="email" v-model="email" />
                </div>
                <div class="flex justify-end gap-2">
                    <Button severity="secondary" @click="visible = false">Cancel</Button>
                    <Button @click="visible = false">Save</Button>
                </div>
            </div>
        </Dialog>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const position = ref('center');
const visible = ref(false);
const username = ref('');
const email = ref('');

const openPosition = (pos) => {
    position.value = pos;
    visible.value = true;
};
<\/script>
```

## Maximizable

Adding maximizable property enables the full screen mode.

```vue
<template>
    <div class="flex justify-center">
        <Button @click="visible = true">Show</Button>
        <Dialog v-model:visible="visible" maximizable modal header="Article Preview" :style="{ width: '50rem' }">
            <div class="flex flex-col gap-4">
                <div class="flex items-center gap-2 text-sm text-surface-500 dark:text-surface-400">
                    <span>Published on Feb 1, 2026</span>
                    <span>·</span>
                    <span>5 min read</span>
                </div>
                <h2 class="text-xl font-bold mt-0 mb-0">Getting Started with Component-Driven Development</h2>
                <p class="leading-relaxed mt-0 mb-0">
                    Component-driven development is an approach that focuses on building loosely coupled, independent components that can be composed together to build complex user interfaces. This methodology promotes reusability, testability, and
                    maintainability.
                </p>
                <p class="leading-relaxed mt-0 mb-0">
                    By breaking down the UI into smaller, self-contained pieces, teams can work in parallel on different parts of the application without stepping on each other's toes. Each component encapsulates its own logic, styles, and behavior,
                    making it easier to reason about and test in isolation.
                </p>
                <p class="leading-relaxed mt-0 mb-0">
                    Modern frameworks and libraries have embraced this pattern, providing tools and conventions that make it straightforward to create, compose, and manage components at scale. The result is a more predictable, scalable, and
                    enjoyable development experience.
                </p>
            </div>
            <template #footer>
                <div class="flex items-center justify-between w-full text-sm text-surface-500 dark:text-surface-400">
                    <span>Last updated: Feb 1, 2026</span>
                    <span>Author: Jane Doe</span>
                </div>
            </template>
        </Dialog>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const visible = ref(false);
<\/script>
```

## Full Screen

A full screen Dialog can be achieved by sizing the component to the viewport with utility classes such as w-screen and h-screen .

```vue
<template>
    <div class="flex justify-center">
        <Button @click="visible = true">View Gallery</Button>
        <Dialog v-model:visible="visible" modal header="Photo Gallery" class="w-screen! h-screen! max-h-screen! rounded-none!">
            <div class="flex flex-col gap-4">
                <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
                    <div v-for="i in 18" :key="i" class="aspect-square rounded-lg bg-surface-100 dark:bg-surface-800 flex items-center justify-center">
                        <ImageIcon class="text-2xl text-surface-400" />
                    </div>
                </div>
                <p class="text-sm text-surface-500 dark:text-surface-400 mt-0 mb-0">Showing 18 of 64 photos</p>
            </div>
        </Dialog>
    </div>
</template>

<script setup>
import { ref } from 'vue';
import ImageIcon from '@primeicons/vue/image';

const visible = ref(false);
<\/script>
```

## Modal

Mask layer behind the Dialog is enabled with the modal property, and dismissableMask allows closing it by clicking outside.

```vue
<template>
    <div class="flex justify-center">
        <Button @click="visible = true">Edit Profile</Button>
        <Dialog v-model:visible="visible" modal dismissableMask header="Edit Profile" :style="{ width: '25rem' }">
            <div class="flex flex-col gap-6">
                <span class="text-surface-500 dark:text-surface-400">Update your information. Click outside the dialog to dismiss.</span>
                <div class="flex flex-col gap-1">
                    <Label for="username" class="font-semibold">Username</Label>
                    <InputText id="username" v-model="username" autoFocus />
                </div>
                <div class="flex flex-col gap-1">
                    <Label for="email" class="font-semibold">Email</Label>
                    <InputText id="email" v-model="email" />
                </div>
                <div class="flex justify-end gap-2">
                    <Button severity="secondary" @click="visible = false">Cancel</Button>
                    <Button @click="visible = false">Save</Button>
                </div>
            </div>
        </Dialog>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const visible = ref(false);
const username = ref('');
const email = ref('');
<\/script>
```

## Without Modal

Mask layer behind the Dialog is configured with the modal property. By default, no modal layer is added.

```vue
<template>
    <div class="flex justify-center">
        <Button @click="visible = true">Show</Button>
        <Dialog v-model:visible="visible" header="Edit Profile" :style="{ width: '25rem' }">
            <div class="flex flex-col gap-6">
                <span class="text-surface-500 dark:text-surface-400">Update your information.</span>
                <div class="flex flex-col gap-1">
                    <Label for="username" class="font-semibold">Username</Label>
                    <InputText id="username" v-model="username" autoFocus />
                </div>
                <div class="flex flex-col gap-1">
                    <Label for="email" class="font-semibold">Email</Label>
                    <InputText id="email" v-model="email" />
                </div>
                <div class="flex justify-end gap-2">
                    <Button severity="secondary" @click="visible = false">Cancel</Button>
                    <Button @click="visible = false">Save</Button>
                </div>
            </div>
        </Dialog>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const visible = ref(false);
const username = ref('');
const email = ref('');
<\/script>
```

## Confirmation

A confirmation dialog can be built by disabling the header close button with closable and providing explicit actions in the content.

```vue
<template>
    <div class="flex justify-center">
        <Button severity="danger" @click="visible = true">Delete Account</Button>
        <Dialog v-model:visible="visible" modal :closable="false" header="Delete your account." :style="{ width: '26rem' }">
            <div class="flex flex-col gap-4">
                <p class="text-surface-500 dark:text-surface-400 text-sm mt-0 mb-0">This action cannot be undone. All of your data, including projects, files, and settings will be permanently removed.</p>
                <div class="flex justify-end gap-2">
                    <Button severity="secondary" @click="visible = false">Cancel</Button>
                    <Button severity="danger" @click="visible = false">Delete</Button>
                </div>
            </div>
        </Dialog>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const visible = ref(false);
<\/script>
```

## Long Content

When content exceeds the available space, the content area scrolls while the header and footer stay fixed.

```vue
<template>
    <div class="flex justify-center">
        <Button @click="visible = true">Inside Scroll</Button>
        <Dialog v-model:visible="visible" modal header="Terms of Service" :style="{ width: '40rem' }">
            <div class="flex flex-col gap-4">
                <div class="flex items-center gap-2">
                    <Tag value="Updated" severity="info" />
                    <span class="text-sm text-surface-500 dark:text-surface-400">Last revised: January 1, 2026</span>
                </div>

                <div>
                    <h3 class="text-base font-semibold mt-0 mb-2">1. Acceptance of Terms</h3>
                    <p class="text-sm leading-relaxed mt-0 mb-0 text-surface-600 dark:text-surface-300">
                        By accessing and using this service, you accept and agree to be bound by the terms and provision of this agreement. If you do not agree to abide by the above, please do not use this service.
                    </p>
                </div>

                <div>
                    <h3 class="text-base font-semibold mt-0 mb-2">2. Use License</h3>
                    <p class="text-sm leading-relaxed mt-0 mb-0 text-surface-600 dark:text-surface-300">
                        Permission is granted to temporarily download one copy of the materials on this service for personal, non-commercial transitory viewing only. This is the grant of a license, not a transfer of title, and under this license
                        you may not modify or copy the materials, use the materials for any commercial purpose, or attempt to decompile or reverse engineer any software contained on this service.
                    </p>
                </div>

                <div>
                    <h3 class="text-base font-semibold mt-0 mb-2">3. Disclaimer</h3>
                    <p class="text-sm leading-relaxed mt-0 mb-0 text-surface-600 dark:text-surface-300">
                        The materials on this service are provided on an 'as is' basis. We make no warranties, expressed or implied, and hereby disclaim and negate all other warranties including, without limitation, implied warranties or conditions
                        of merchantability, fitness for a particular purpose, or non-infringement of intellectual property or other violation of rights.
                    </p>
                </div>

                <div>
                    <h3 class="text-base font-semibold mt-0 mb-2">4. Limitations</h3>
                    <p class="text-sm leading-relaxed mt-0 mb-0 text-surface-600 dark:text-surface-300">
                        In no event shall we or our suppliers be liable for any damages (including, without limitation, damages for loss of data or profit, or due to business interruption) arising out of the use or inability to use the materials on
                        this service, even if we or an authorized representative has been notified orally or in writing of the possibility of such damage.
                    </p>
                </div>

                <div>
                    <h3 class="text-base font-semibold mt-0 mb-2">5. Privacy Policy</h3>
                    <p class="text-sm leading-relaxed mt-0 mb-0 text-surface-600 dark:text-surface-300">
                        Your privacy is important to us. Our Privacy Policy explains how we collect, use, and protect your personal information when you use our service. By using our service, you agree to the collection and use of information in
                        accordance with our Privacy Policy. We are committed to ensuring that your information is secure and handled responsibly.
                    </p>
                </div>

                <div>
                    <h3 class="text-base font-semibold mt-0 mb-2">6. User Accounts</h3>
                    <p class="text-sm leading-relaxed mt-0 mb-0 text-surface-600 dark:text-surface-300">
                        When you create an account with us, you must provide information that is accurate, complete, and current at all times. Failure to do so constitutes a breach of the Terms, which may result in immediate termination of your
                        account on our service. You are responsible for safeguarding the password that you use to access the service and for any activities or actions under your password.
                    </p>
                </div>

                <div>
                    <h3 class="text-base font-semibold mt-0 mb-2">7. Intellectual Property</h3>
                    <p class="text-sm leading-relaxed mt-0 mb-0 text-surface-600 dark:text-surface-300">
                        The service and its original content, features, and functionality are and will remain the exclusive property of the company and its licensors. The service is protected by copyright, trademark, and other laws of both domestic
                        and foreign countries. Our trademarks and trade dress may not be used in connection with any product or service without the prior written consent of the company.
                    </p>
                </div>

                <div>
                    <h3 class="text-base font-semibold mt-0 mb-2">8. Termination</h3>
                    <p class="text-sm leading-relaxed mt-0 mb-0 text-surface-600 dark:text-surface-300">
                        We may terminate or suspend your account immediately, without prior notice or liability, for any reason whatsoever, including without limitation if you breach the Terms. Upon termination, your right to use the service will
                        immediately cease. If you wish to terminate your account, you may simply discontinue using the service or contact us to request account deletion.
                    </p>
                </div>

                <div>
                    <h3 class="text-base font-semibold mt-0 mb-2">9. Indemnification</h3>
                    <p class="text-sm leading-relaxed mt-0 mb-0 text-surface-600 dark:text-surface-300">
                        You agree to defend, indemnify, and hold harmless the company and its licensee and licensors, and their employees, contractors, agents, officers, and directors, from and against any and all claims, damages, obligations,
                        losses, liabilities, costs or debt, and expenses, including but not limited to attorney's fees, resulting from or arising out of your use and access of the service, or a breach of these Terms.
                    </p>
                </div>

                <div>
                    <h3 class="text-base font-semibold mt-0 mb-2">10. Governing Law</h3>
                    <p class="text-sm leading-relaxed mt-0 mb-0 text-surface-600 dark:text-surface-300">
                        These terms and conditions are governed by and construed in accordance with applicable laws and you irrevocably submit to the exclusive jurisdiction of the courts in that location. Any claim relating to this service shall be
                        governed by the laws without regard to its conflict of law provisions.
                    </p>
                </div>

                <div>
                    <h3 class="text-base font-semibold mt-0 mb-2">11. Changes to Terms</h3>
                    <p class="text-sm leading-relaxed mt-0 mb-0 text-surface-600 dark:text-surface-300">
                        We reserve the right, at our sole discretion, to modify or replace these Terms at any time. If a revision is material we will try to provide at least 30 days' notice prior to any new terms taking effect. What constitutes a
                        material change will be determined at our sole discretion. By continuing to access or use our service after those revisions become effective, you agree to be bound by the revised terms.
                    </p>
                </div>
            </div>
            <template #footer>
                <Button severity="secondary" @click="visible = false">Decline</Button>
                <Button @click="visible = false">Accept</Button>
            </template>
        </Dialog>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const visible = ref(false);
<\/script>
```

## Responsive

Dialog dimensions can be made responsive with breakpoint-based utility classes applied directly to the component.

```vue
<template>
    <div class="flex justify-center">
        <Button @click="visible = true">New Event</Button>
        <Dialog v-model:visible="visible" modal header="Create Event" class="w-[90vw] md:w-[75vw] lg:w-[50vw]">
            <div class="flex flex-col gap-4">
                <div class="flex flex-col gap-1">
                    <Label for="eventName" class="text-sm font-semibold">Event Name</Label>
                    <InputText id="eventName" v-model="eventName" placeholder="e.g. Team Standup" autoFocus />
                </div>
                <div class="flex flex-col md:flex-row gap-4">
                    <div class="flex flex-col gap-1 flex-1">
                        <Label for="organizer" class="text-sm font-semibold">Organizer</Label>
                        <InputText id="organizer" v-model="organizer" placeholder="Name" />
                    </div>
                    <div class="flex flex-col gap-1 flex-1">
                        <Label for="email" class="text-sm font-semibold">Email</Label>
                        <InputText id="email" v-model="email" placeholder="organizer@example.com" />
                    </div>
                </div>
                <div class="flex flex-col gap-1">
                    <Label for="location" class="text-sm font-semibold">Location</Label>
                    <InputText id="location" v-model="location" placeholder="Add a location or video link" />
                </div>
                <div class="flex flex-col gap-1">
                    <Label for="description" class="text-sm font-semibold">Description</Label>
                    <InputText id="description" v-model="description" placeholder="Event details" />
                </div>
                <div class="flex flex-col sm:flex-row justify-end gap-2 mt-2">
                    <Button severity="secondary" @click="visible = false">Cancel</Button>
                    <Button @click="visible = false">Create Event</Button>
                </div>
            </div>
        </Dialog>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const visible = ref(false);
const eventName = ref('');
const organizer = ref('');
const email = ref('');
const location = ref('');
const description = ref('');
<\/script>
```

## Headless

Headless mode is enabled by defining a container slot that lets you implement entire UI instead of the default elements.

```vue
<template>
    <div class="flex justify-center">
        <Button @click="visible = true">
            <User />
            Login
        </Button>

        <Dialog v-model:visible="visible" pt:root:class="border-0! bg-transparent!" pt:mask:class="backdrop-blur-xs">
            <template #container="{ closeCallback }">
                <div class="flex flex-col px-8 py-8 gap-5 rounded-2xl" style="border-radius: 12px; background-image: radial-gradient(circle at left top, var(--p-primary-400), var(--p-primary-700))">
                    <svg width="35" height="40" viewBox="0 0 35 40" fill="none" xmlns="http://www.w3.org/2000/svg" class="block mx-auto">
                        <path
                            d="M25.87 18.05L23.16 17.45L25.27 20.46V29.78L32.49 23.76V13.53L29.18 14.73L25.87 18.04V18.05ZM25.27 35.49L29.18 31.58V27.67L25.27 30.98V35.49ZM20.16 17.14H20.03H20.17H20.16ZM30.1 5.19L34.89 4.81L33.08 12.33L24.1 15.67L30.08 5.2L30.1 5.19ZM5.72 14.74L2.41 13.54V23.77L9.63 29.79V20.47L11.74 17.46L9.03 18.06L5.72 14.75V14.74ZM9.63 30.98L5.72 27.67V31.58L9.63 35.49V30.98ZM4.8 5.2L10.78 15.67L1.81 12.33L0 4.81L4.79 5.19L4.8 5.2ZM24.37 21.05V34.59L22.56 37.29L20.46 39.4H14.44L12.34 37.29L10.53 34.59V21.05L12.42 18.23L17.45 26.8L22.48 18.23L24.37 21.05ZM22.85 0L22.57 0.69L17.45 13.08L12.33 0.69L12.05 0H22.85Z"
                            fill="var(--p-primary-700)"
                        />
                        <path
                            d="M30.69 4.21L24.37 4.81L22.57 0.69L22.86 0H26.48L30.69 4.21ZM23.75 5.67L22.66 3.08L18.05 14.24V17.14H19.7H20.03H20.16H20.2L24.1 15.7L30.11 5.19L23.75 5.67ZM4.21002 4.21L10.53 4.81L12.33 0.69L12.05 0H8.43002L4.22002 4.21H4.21002ZM21.9 17.4L20.6 18.2H14.3L13 17.4L12.4 18.2L12.42 18.23L17.45 26.8L22.48 18.23L22.5 18.2L21.9 17.4ZM4.79002 5.19L10.8 15.7L14.7 17.14H14.74H15.2H16.85V14.24L12.24 3.09L11.15 5.68L4.79002 5.2V5.19Z"
                            fill="var(--p-primary-200)"
                        />
                    </svg>
                    <div class="inline-flex flex-col gap-2">
                        <label for="username" class="text-primary-50 font-semibold text-sm">Username</label>
                        <InputText id="username" class="bg-white/20! border-0! p-3! text-primary-50! w-80"></InputText>
                    </div>
                    <div class="inline-flex flex-col gap-2">
                        <label for="password" class="text-primary-50 font-semibold text-sm">Password</label>
                        <InputText id="password" class="bg-white/20! border-0! p-3! text-primary-50! w-80" type="password"></InputText>
                    </div>
                    <div class="flex items-center gap-4">
                        <Button @click="closeCallback" variant="text" class="p-3! w-full text-primary-50! border! border-white/30! hover:bg-white/10!">Cancel</Button>
                        <Button @click="closeCallback" variant="text" class="p-3! w-full text-primary-50! border! border-white/30! hover:bg-white/10!">Sign-In</Button>
                    </div>
                </div>
            </template>
        </Dialog>
    </div>
</template>

<script setup>
import { ref } from "vue";
import User from '@primeicons/vue/user';

const visible = ref(false);
<\/script>
```

## Accessibility

Screen Reader Dialog component uses dialog role along with aria-labelledby referring to the header element however any attribute is passed to the root element so you may use aria-labelledby to override this default behavior. In addition aria-modal is added since focus is kept within the popup. It is recommended to use a trigger component that can be accessed with keyboard such as a button, if not adding tabIndex would be necessary. Trigger element also requires aria-expanded and aria-controls to be handled explicitly. Close element is a button with an aria-label that refers to the aria.close property of the locale API by default, you may use closeButtonProps to customize the element and override the default aria-label . Maximize element is a button with an aria-label that refers to the aria.maximizeLabel and aria.minimizeLabel property of the locale API. It cannot be customized using the maximizeButtonProps . Overlay Keyboard Support Key Function tab Moves focus to the next the focusable element within the dialog if modal is true. Otherwise, the focusable element in the page tab sequence. shift + tab Moves focus to the previous the focusable element within the dialog if modal is true. Otherwise, the focusable element in the page tab sequence. escape Closes the dialog if closeOnEscape is true. Close Button Keyboard Support Key Function enter Closes the dialog. space Closes the dialog.

```vue
<template>
    <Button @click="visible = true" :aria-controls="visible ? 'dlg' : null" :aria-expanded="visible ? true : false">
        <ExternalLink />
        Show
    </Button>

    <Dialog id="dlg" header="Header" v-model:visible="visible" :style="{ width: '50vw' }">
        <p>Content</p>
    </Dialog>
</template>

<script setup>
import ExternalLink from '@primeicons/vue/external-link';
<\/script>
```

## Dialog API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| header | string | - | Title content of the dialog. |
| footer | string | - | Footer content of the dialog. |
| visible | boolean | false | Specifies the visibility of the dialog. |
| modal | boolean | false | Defines if background should be blocked when dialog is displayed. |
| contentStyle | any | - | Style of the content section. |
| contentClass | any | - | Style class of the content section. |
| contentProps | HTMLAttributes | - | Used to pass all properties of the HTMLDivElement to the overlay Dialog inside the component. |
| closable | boolean | true | Adds a close icon to the header to hide the dialog. |
| dismissableMask | boolean | false | Specifies if clicking the modal background should hide the dialog. |
| closeOnEscape | boolean | true | Specifies if pressing escape key should hide the dialog. |
| showHeader | boolean | true | Whether to show the header or not. |
| blockScroll | boolean | false | Whether background scroll should be blocked when dialog is visible. |
| baseZIndex | number | 0 | Base zIndex value to use in layering. |
| autoZIndex | boolean | true | Whether to automatically manage layering. |
| position | any | center | Position of the dialog. |
| maximizable | boolean | false | Whether the dialog can be displayed full screen. |
| breakpoints | DialogBreakpoints | - | Object literal to define widths per screen size. |
| draggable | boolean | true | Enables dragging to change the position using header. |
| keepInViewport | boolean | true | Keeps dialog in the viewport when dragging. |
| minX | number | 0. | Minimum value for the left coordinate of dialog in dragging. |
| minY | number | 0 | Minimum value for the top coordinate of dialog in dragging. |
| appendTo | any | body | A valid query selector or an HTMLElement to specify where the dialog gets attached. |
| style | any | - | Style of the dynamic dialog. |
| closeIcon | string | - | Icon to display in the dialog close button. |
| maximizeIcon | string | - | Icon to display in the dialog maximize button when dialog is not maximized. |
| minimizeIcon | string | - | Icon to display in the dialog maximize button when dialog is minimized. |
| closeButtonProps | object | - | Used to pass all properties of the ButtonProps to the Button component. |
| maximizeButtonProps | object | - | Used to pass all properties of the ButtonProps to the Button component. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | DialogPassThroughOptionType<T> | Used to pass attributes to the root's DOM element. |
| header | DialogPassThroughOptionType<T> | Used to pass attributes to the header's DOM element. |
| title | DialogPassThroughOptionType<T> | Used to pass attributes to the header title's DOM element. |
| headerActions | DialogPassThroughOptionType<T> | Used to pass attributes to the header actions' DOM element. |
| pcMaximizeButton | any | Used to pass attributes to the maximize Button component. |
| pcCloseButton | any | Used to pass attributes to the close Button component. |
| content | DialogPassThroughOptionType<T> | Used to pass attributes to the content's DOM element. |
| footer | DialogPassThroughOptionType<T> | Used to pass attributes to the footer's DOM element. |
| mask | DialogPassThroughOptionType<T> | Used to pass attributes to the mask's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |
| transition | DialogPassThroughTransitionType<T> | Used to control Vue Transition API. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-dialog-mask | Class name of the mask element |
| p-dialog | Class name of the root element |
| p-dialog-header | Class name of the header element |
| p-dialog-title | Class name of the title element |
| p-dialog-header-actions | Class name of the header actions element |
| p-dialog-maximize-button | Class name of the maximize button element |
| p-dialog-close-button | Class name of the close button element |
| p-dialog-content | Class name of the content element |
| p-dialog-footer | Class name of the footer element |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| dialog.background | --p-dialog-background | Background of root |
| dialog.border.color | --p-dialog-border-color | Border color of root |
| dialog.color | --p-dialog-color | Color of root |
| dialog.border.radius | --p-dialog-border-radius | Border radius of root |
| dialog.shadow | --p-dialog-shadow | Shadow of root |
| dialog.header.padding | --p-dialog-header-padding | Padding of header |
| dialog.header.gap | --p-dialog-header-gap | Gap of header |
| dialog.title.font.size | --p-dialog-title-font-size | Font size of title |
| dialog.title.font.weight | --p-dialog-title-font-weight | Font weight of title |
| dialog.content.padding | --p-dialog-content-padding | Padding of content |
| dialog.footer.padding | --p-dialog-footer-padding | Padding of footer |
| dialog.footer.gap | --p-dialog-footer-gap | Gap of footer |
