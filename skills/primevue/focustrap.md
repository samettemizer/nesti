# Focus Trap

Focus Trap keeps focus within a certain DOM element while tabbing.

## Basic

FocusTrap is applied to a container element with the v-focustrap directive.

```vue
<template>
    <div class="flex justify-center">
        <div v-focustrap class="w-full sm:w-80 flex flex-col gap-5">
            <IconField>
                <InputIcon>
                    <User />
                </InputIcon>
                <InputText id="input" v-model="name" type="text" placeholder="Name" autofocus fluid />
            </IconField>

            <IconField>
                <InputIcon>
                    <Envelope />
                </InputIcon>
                <InputText id="email" v-model="email" type="email" placeholder="Email" fluid />
            </IconField>

            <div class="flex items-center gap-2">
                <Checkbox id="accept" v-model="accept" name="accept" value="Accept" />
                <label for="accept" class="text-sm">I agree to the terms and conditions.</label>
            </div>

            <Button type="submit" class="mt-2 w-full">Submit</Button>
        </div>
    </div>
</template>

<script setup>
import { ref } from 'vue';
import Envelope from '@primeicons/vue/envelope';
import User from '@primeicons/vue/user';

const name = ref();
const email = ref();
const accept = ref(false);
<\/script>
```

## Focus Trap API

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | FocusTrapDirectivePassThroughOptionType | Used to pass attributes to the root's DOM element. |
| firstFocusableElement | FocusTrapDirectivePassThroughOptionType | Used to pass attributes to the first focusable element's DOM element. |
| lastFocusableElement | FocusTrapDirectivePassThroughOptionType | Used to pass attributes to the last focusable element's DOM element. |
| hooks | DirectiveHooks<any, any> | Used to manage all lifecycle hooks. |

### Theming
