<script setup lang="ts">
import { onMounted, ref } from 'vue'

const props = defineProps<{ task_id: string }>()

const message = ref('Task page loaded successfully')

console.log('Task ID:', props.task_id)

onMounted(() => {
  console.log('Simple task page mounted')
})
</script>

<template>
  <div class="p-8">
    <h1 class="text-2xl font-bold mb-4">任务页面 - {{ props.task_id }}</h1>
    <p>{{ message }}</p>
  </div>
</template>