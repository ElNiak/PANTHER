module.exports = function ({ template, types: t }) {
  return {
    visitor: {
      ImportDeclaration (nodePath, { opts }) {
        const specifiers = nodePath.get('specifiers');
        if (specifiers && specifiers.length) {
          specifiers.forEach(spec => {
            if (spec.isImportDefaultSpecifier()) {
              const importedModule = spec.parent.source.value;
              const varName = spec.node.local.name;
              if (translate(opts.modules, importedModule)) {
                const buildRequire = template(`const IMPORT_NAME = require(SOURCE);`);
                const newNode = buildRequire({
                  IMPORT_NAME: t.identifier(varName),
                  SOURCE: t.stringLiteral(importedModule)
                });
                nodePath.replaceWith(newNode);
              }
            }
          });
        }
      }
    }
  };

  function translate (modules, name) {
    modules = typeof modules === 'string' ? [ modules ] : modules;
    if (Array.isArray(modules)) {
      return modules.includes(name);
    } else return true;
  }
};
