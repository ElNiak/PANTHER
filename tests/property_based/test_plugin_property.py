# from hypothesis import given, strategies as st

# @given(plugin_name=st.text(min_size=1, max_size=20))
# def test_load_plugin_property(plugin_name):
#     try:
#         plugin = load_plugin(plugin_name)
#         assert plugin.is_valid()
#     except ValueError:
#         pass  # Expect some invalid plugin names to raise errors
