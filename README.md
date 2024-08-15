# actionsheets

**Actionsheets** is an open-source (hobby) project with a different take on cheatsheets. 
Standard cheatsheets are great for getting started, but don't get into the details for advanced or complex use cases. 
This is where actionsheets come in.

This Python package provides a large collection of code snippets, and can render them in the form of _actionsheets_. Actionsheets are grouped look-up tables by action/intended outcome, and a code snippet to achieve it.
The package is intended for (new) developers to quickly look-up how to perform common actions for the given topic, but also contains some more advanced actions.

The package can print actionsheets in the console with coloring and syntax highlighting, but ideally, the package is used by other (better) front-end implementations. See the [streamlit dashboard](https://github.com/niekdt/actionsheets-streamlit) implementation, for example.


## How do actionsheets differ from cheatsheets?
- Actionsheets are expressed in terms of a desired *action* or result, and the code snippet(s) to achieve it.
  - This is a more natural way to look up code snippets. Especially useful for beginners.
- Actions may be complex or comprise multiple steps.
  - Actions are not limited to the direct functionality provided by the package API. 
  - Cheatsheets typically lack more advanced compound use cases.
- Code snippets are data; enabling dynamic generation of sheets depending on user queries
  - Sheets can therefore be more feature-complete, as they do not need fit on a single page.
    
This way of organizing sheets is especially useful for packages or functions with powerful versatile functionality, where merely listing the API does not cover the full capabilities. 

## Install
To install the latest release:
```shell
pip install actionsheets
```

To install according to the latest commit:
```shell
pip install git+https://github.com/niekdt/actionsheets.git
```

```shell
poetry add git+https://github.com/niekdt/actionsheets.git
```

## Contributing
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


## Actionsheet structure
Sheets are hierarchically structured using sections. The main sections are:

1. **Create**  
How to define, instantiate or create the data type, possibly from other types.  
_Examples: define a date, parse date from string, create set from a list of values._
2. **Test**  
Check or assess something about the object.  
_Examples: is it empty? does it contain a given value?_
3. **Extract** 
Get properties, attributes, or other information about the object _of a different type than the object_ (typically scalars).  
_Examples: length of a list, element value at a given index, max value among elements._
4. **Derive / Update**
Create a derived or altered object from the given object, preserving the object type, or _update_ the object in-place / by-reference.  
_Examples: head of a list, slicing a string, selecting conditional rows from a data frame._
5. **Convert**
Export / represent the object as a different data type.  
_Examples: datetime as string, dictionary as list of key-value pairs, data frame as matrix._

### Extract
Get properties, attributes, or other information about the object _of a different type than the object_ (typically scalars). 

| Subcategory    | Description                                                                              | Examples                                                                  |
|----------------|------------------------------------------------------------------------------------------|---------------------------------------------------------------------------|
| **Properties** | Retrieve properties or attributes of the object.                                         | Length of a list, number of columns of a data frame.                      |
| **Find**       | Attempt to find a value or index of an object, typically with index output.              | Find max value, find index of min value, find key of most frequent value. |
| **Aggregate**  | Aggregate the object in a way that involves a computation, typically with scalar output. | Sum all elements of a list, number of occurrences per value               |


### Derive / update
| Subcategory   | Description                                                                                                                                                         | Examples                                                                                                         |
|---------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------|
| **Transform** | Apply a [transformation](https://en.wikipedia.org/wiki/Data_transformation_(statistics)) to the object or each of its elements, preserving the shape of the object. | Element-wise operations such as adding a constant to a vector, or computing the cumulative sum over the elements |
| **Order**     | Change the order of elements, but not their values.                                                                                                                 | Reversing the elements of a list, sorting a data frame by column values                                          |
| **Reshape**   | Change the shape of the object, but preserves all elements.                                                                                                         | Transposing a matrix, converting a data frame to narrow format.                                                  |
| **Grow**      | Possibly increase the number of elements of the object.                                                                                                             | Appending elements to a list, replicating elements.                                                              |
| **Shrink**    | Possibly reduce the number of elements of the object.                                                                                                               | Removing elements from a list, removing duplicates.                                                              |
| **Combine**   | Combine, merge or join two or more objects.                                                                                                                         | Stacking lists, set union, joining two data frames.                                                              |


## Motivation
My motivation for building this curated database of code snippet is out of frustration of the worsening state of the internet in quickly finding short answers to straightforward queries.

- Many website have the code snippet(s) buried between tons of irrelevant text just for SEO optimization.
- The quality of (accepted) answers on Stackoverflow is severely lacking for some programming languages:
  - Answers are out of date
  - Answers are overly complicated, inefficient, or nonfunctional (contributions by beginners)
  - For the future, this also means that the answers by any LLM are going to have the same issues. 
- The answer on the site was for a different question
- The answer on the site was for a more narrow question
- With the increasing usage of LLMs, the problem of bloated low-quality answer results will only get worse.
     
