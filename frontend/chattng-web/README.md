# React + TypeScript + Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react/README.md) uses [Babel](https://babeljs.io/) for Fast Refresh
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react-swc) uses [SWC](https://swc.rs/) for Fast Refresh

## Expanding the ESLint configuration

If you are developing a production application, we recommend updating the configuration to enable type aware lint rules:

- Configure the top-level `parserOptions` property like this:

```js
export default tseslint.config({
  languageOptions: {
    // other options...
    parserOptions: {
      project: ['./tsconfig.node.json', './tsconfig.app.json'],
      tsconfigRootDir: import.meta.dirname,
    },
  },
})
```

- Replace `tseslint.configs.recommended` to `tseslint.configs.recommendedTypeChecked` or `tseslint.configs.strictTypeChecked`
- Optionally add `...tseslint.configs.stylisticTypeChecked`
- Install [eslint-plugin-react](https://github.com/jsx-eslint/eslint-plugin-react) and update the config:

```js
// eslint.config.js
import react from 'eslint-plugin-react'

export default tseslint.config({
  // Set the react version
  settings: { react: { version: '18.3' } },
  plugins: {
    // Add the react plugin
    react,
  },
  rules: {
    // other rules...
    // Enable its recommended rules
    ...react.configs.recommended.rules,
    ...react.configs['jsx-runtime'].rules,
  },
})
```

## Mobile Testing Guide

### Local Testing with Browser DevTools
1. Chrome/Edge:
   - Open Developer Tools (F12)
   - Click the "Toggle Device Toolbar" icon (or Ctrl+Shift+M)
   - Select a device from the dropdown (e.g., iPhone 12, Galaxy S20)
   - Test interactions in this simulated environment

2. Firefox:
   - Open Developer Tools (F12)
   - Click the "Responsive Design Mode" icon (or Ctrl+Shift+M)
   - Select device dimensions from the presets

### Cloud-Based Testing (Real Devices)
For testing on actual iOS devices without owning hardware:

1. **BrowserStack**: 
   - Sign up for a free trial at [BrowserStack](https://www.browserstack.com/)
   - Choose Live testing for interactive sessions or App Automate for automated tests
   - Access real iOS devices for accurate testing
   - Use the following command to test with BrowserStack:
   ```
   # If running locally
   npm run dev 
   
   # Then share your local app using:
   npx browserstack-cypress run --local
   ```

2. **LambdaTest**:
   - Sign up for a free trial at [LambdaTest](https://www.lambdatest.com/)
   - Similar functionality to BrowserStack with its own set of iOS devices

### Physical Device Testing via Network
If friends have iOS devices, you can easily share your development app:
1. Ensure your computer and their device are on the same network
2. Find your local IP address using `ipconfig` (Windows) or `ifconfig` (Mac/Linux)
3. Update the dev script in package.json:
   ```json
   "scripts": {
     "dev": "vite --host",
     ...
   }
   ```
4. Run `npm run dev` and share the network URL with friends

### Debugging iOS-Specific Issues
Common iOS issues to check:
- Safari-specific CSS issues
- Touch event handling differences
- iOS PWA/homescreen compatibility
- Mobile Safari viewport quirks
