#


### setup_cytoscape
```python
.setup_cytoscape()
```


----


### setup_quic_model
```python
.setup_quic_model(
   ivy_test_path
)
```


----


### get_relations
```python
.get_relations(
   mapping
)
```


----


### add_assertion
```python
.add_assertion(
   in_action, mapping, splitted_line
)
```


----


### setup_assertions
```python
.setup_assertions(
   act, in_action, in_action_assumptions, in_action_guarantees, line, mapping
)
```


----


### find_external_action
```python
.find_external_action(
   action_name, current_action, file, found, mapping
)
```


----


### find_external_object_action
```python
.find_external_object_action(
   action_name, current_action, file, found, mapping
)
```


----


### get_action_implementation
```python
.get_action_implementation(
   content, implem_elem, line, new_file, splitted_line
)
```


----


### get_called_action_implementation
```python
.get_called_action_implementation(
   content, line, new_file, splitted_line
)
```


----


### get_action_return
```python
.get_action_return(
   current_elem, signature
)
```


----


### get_action_parameters
```python
.get_action_parameters(
   action_parameters, current_elem
)
```


----


### init_mapping
```python
.init_mapping(
   action_name, content, has_implem, is_init, is_module_object,
   is_module_object_present, line, mapping, object_name, splitted_line
)
```


----


### get_module_object_attributes
```python
.get_module_object_attributes(
   action_name, content, line, mapping, object_name, splitted_line
)
```


----


### check_object_present
```python
.check_object_present(
   action_name, content, is_module_object_present, line, mapping, object_name,
   splitted_line
)
```


----


### init_tp_mapping
```python
.init_tp_mapping(
   content, mapping, splitted_line
)
```


----


### get_prefix
```python
.get_prefix(
   splitted_line
)
```


----


### change_permission
```python
.change_permission(
   ivy_test_path
)
```


----


### split_line
```python
.split_line(
   line
)
```

