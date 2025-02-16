---
search:
  exclude: true
---

# Contributing
This website is a front-end for the [actionsheets](https://github.com/niekdt/actionsheets) package.
Actionsheets are defined using [TOML](https://toml.io/) files. 
This makes it very easy to define a hierarchy of code snippets in a readable way.

Defining a code snippet belonging to the _Create_ section of the respective actionsheet file is as simple as:
```toml
[create.list]
action = "Define a list"
code = "x = ['apple', 'pear', 'banana']"
details = "You can define as many items as you like"
```

For submitting code snippets or complete actionsheets, submit a PR to [actionsheets on Github](https://github.com/niekdt/actionsheets).
