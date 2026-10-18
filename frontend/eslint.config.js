import js from '@eslint/js'
import prettier from 'eslint-config-prettier/flat'
import pluginVue from 'eslint-plugin-vue'
import { defineConfig, globalIgnores } from 'eslint/config'
import globals from 'globals'

const noParentImports = { regex: '^\\.\\./', message: "Import from outside this folder with the '@/' alias." }

export default defineConfig([
  // public/ is copied into dist as-is and is not part of the bundle.
  globalIgnores(['dist/', 'public/']),
  js.configs.recommended,
  pluginVue.configs['flat/essential'],
  {
    languageOptions: { globals: globals.browser },
    rules: {
      // Pages and base components here are single words (Keys.vue, Modal.vue).
      'vue/multi-word-component-names': 'off',
      // `vite build` does not check templates, so report names and components they cannot resolve.
      'vue/no-undef-components': ['error', { ignorePatterns: ['RouterLink', 'RouterView'] }],
      'vue/no-undef-properties': 'error',
      'no-restricted-imports': ['error', { patterns: [noParentImports] }],
    },
  },
  {
    // Endpoints are defined once in src/api/*; pages and components call those, not http.
    files: ['src/views/**', 'src/components/**', 'src/layouts/**', 'src/composables/**'],
    rules: {
      'no-restricted-imports': [
        'error',
        {
          paths: [{ name: '@/api/http', message: 'Call the endpoint module in src/api instead.' }],
          patterns: [noParentImports],
        },
      ],
    },
  },
  {
    files: ['*.config.js'],
    languageOptions: { globals: globals.node },
  },
  // Formatting is Prettier's job; this turns off the stylistic rules that would conflict with it.
  prettier,
])
