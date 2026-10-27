import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";

const html=readFileSync(new URL("../index.html",import.meta.url),"utf8");
const css=readFileSync(new URL("../rdi-responsive.css",import.meta.url),"utf8");

test("RDI home loads full-window layout last, without affecting YouTube broadcast view",()=>{
  assert.match(html,/<link rel="stylesheet" href="\.\/rdi-responsive\.css\?v=20261027-fullscreen-1">/);
  assert.ok(html.indexOf("rdi-responsive.css") > html.indexOf("rdi-featured.css"));
  assert.ok(html.indexOf("rdi-responsive.css") < html.indexOf("</head>"));
  assert.match(css,/html:not\(\.youtube-news\) body>main\{[\s\S]*?width:100%;[\s\S]*?max-width:none;/);
  assert.doesNotMatch(css,/^[^\n]*html\.youtube-news [^\n]+\{/m);
});
test("desktop layouts fill viewport and present banner, player and editorial columns",()=>{
  assert.match(css,/@media\(min-width:1100px\)/);
  assert.match(css,/grid-template-columns:minmax\(0,1\.5fr\) minmax\(365px,\.86fr\)/);
  assert.match(css,/grid-template-columns:minmax\(0,1\.55fr\) repeat\(2,minmax\(0,1fr\)\)/);
  assert.match(css,/\.news-section \.news-list\{\s*grid-template-columns:repeat\(4,minmax\(0,1fr\)\)/);
});
test("phone and small-screen layouts use readable stacked cards",()=>{
  assert.match(css,/@media\(max-width:699px\)/);
  assert.match(css,/\.rdi-featured-grid\{grid-template-columns:1fr;/);
  assert.match(css,/\.rdi-featured-story:not\(:first-child\) \.rdi-featured-link\{flex-direction:row;/);
  assert.match(css,/@media\(max-width:400px\)/);
  assert.match(css,/\.news-section \.news-list\{grid-template-columns:1fr\}/);
  assert.match(css,/overflow-x:clip/);
});
