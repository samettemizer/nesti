<template>
    <div class="flex items-center justify-center min-h-screen">
        <div class="flex flex-col items-center gap-4">
            <span class="text-primary font-bold text-3xl">404</span>
            <h1 class="text-surface-900 dark:text-surface-0 font-bold text-3xl">Not Found</h1>
            <p class="text-muted-color">Requested resource is not available.</p>
            <Button as="router-link" label="Go to Dashboard" to="/" />
        </div>
    </div>
</template>
