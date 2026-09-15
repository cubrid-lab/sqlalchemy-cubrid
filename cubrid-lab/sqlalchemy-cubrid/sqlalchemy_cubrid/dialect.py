@@ -235,7 +235,6 @@ class CubridDialect(Dialect):
         # self.supports_native_decimal = True
         self.supports_native_boolean = True
         self.supports_empty_in_list = True
-        self.implicit_returning = False

     def create_connect_args(self, url):
         args = super().create_connect_args(url)