/*
*/

import replace from "rollup-plugin-replace";
import resolve from "rollup-plugin-node-resolve";
import commonjs from "rollup-plugin-commonjs";
import { terser } from "rollup-plugin-terser";
import vue from "rollup-plugin-vue";
import postcss from "rollup-plugin-postcss";

import { renderFile } from "pug";

import { dirname } from "path";
import { readFileSync, writeFile, mkdir } from "fs";

const isProduction = process.env.NODE_ENV === "production";

const version = readFileSync("../VERSION").toString().trim();

const makeHTMLBundleWithInlineCSSAndJSPlugin = function (options) {
    return {
        name: "makeHTMLBundleWithInlineCSSAndJS",
        generateBundle(outputOptions, bundle){
          var js = "", css = "";
          
          const bundleEntries = Object.entries(bundle);
          for (const [key, value] of bundleEntries) {
            if (key.endsWith("js")) {
              js += value.code;
            } else if (key.endsWith("css")) {
              css += value.source;
            }
            delete bundle[key]
          }
          
          var html = renderFile(options.inputTemplate, {
            css, js,
            pageTitle: "mindandbrain/qualitycheck " + version
          });
          
          mkdir(dirname(options.outputFileName), { 
            recursive: true 
          }, (err) => {
            console.log(err);
            if (err) throw err;
          });
          
          writeFile(options.outputFileName, html, (err) => {
            console.log(err);
            if (err) throw err;
          });
        }
    };
};

export default (async () => ({
  input: "src/index.js",
  output: {
    name: "qualitycheck",
    file: "index.js",
    format: "iife"
  },
  plugins: [
    resolve({
      browser: true
    }),
    replace({
      "process.env.NODE_ENV": JSON.stringify(
         isProduction ? "production" : "development"
       )
    }),
    commonjs(),
    vue({
      css: false,
      compileTemplate: true,
      template: {
        isProduction,
        compilerOptions: { preserveWhitespace: false }
      },
    }),
    postcss({
      extract: true
    }),
    isProduction && terser({
      output: {
        comments: "some",
        ecma: 6
      }
    }),
    makeHTMLBundleWithInlineCSSAndJSPlugin({
      inputTemplate: "src/index.pug",
      outputFileName: "dist/index.html"
    })
  ]
}))();