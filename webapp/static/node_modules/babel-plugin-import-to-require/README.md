# babel-plugin-import-to-require

Remaps `import` statements to `require()` statements. This is mostly useful alongside later static analysis tools (like glslify), where Babel import inter-op can often make static analysis difficult or impossible.

In:

```js
import foobar from 'foo';
console.log(foobar());
```

Out:

```js
const foobar = require('foo');
console.log(foobar());
```

> :warning: This only handles basic import specifiers (i.e. the above format), and does not support things like wildcard imports, destructuring, namespaces, etc. Feel free to submit a PR if you need this feature.

## Installation

```sh
$ npm install babel-plugin-import-to-require
```

## Usage

The `modules` option can be used to narrow down to a specific list of modules to remap, ignoring all other import statements. If no parameter is specified, _all_ import statements will be remapped.

### Via `.babelrc` (Recommended)

**.babelrc**

```json
{
  "plugins": [
    [ "import-to-require", { "modules": [ "foo" ] } ]
  ]
}
```

### Via CLI

```sh
$ babel --plugins import-to-require script.js
```

### Via Node API

```javascript
require('babel').transform('code', {
  plugins: [
    [ 'import-to-require' , { modules: [ 'foo' ] } ]
  ]
});
```
