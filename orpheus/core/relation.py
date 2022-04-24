class RelationNotExistError(Exception):
  def __init__(self, tablename):
      self.name = tablename
  def __str__(self):
      return "Relation %s does not exist" % self.name

class RelationOverwriteError(Exception):
  def __init__(self, tablename):
      self.name = tablename
  def __str__(self):
      return "Relation %s exists, add flag to allow overwrite" % self.name

class ReservedRelationError(Exception):
  def __init__(self, tablename):
      self.name = tablename
  def __str__(self):
      return "Relation %s is a reserved name, please use a different one" % self.name

class ColumnNotExistError(Exception):
  def __init__(self, column):
      self.name = column
  def __str__(self):
      return "Column %s does not exist" % self.name

class RelationManager(object):
    def __init__(self, conn):
      self.conn = conn;

    def get_datatable_attribute(self, from_table):
      selectTemplate = "SELECT column_name, data_type from INFORMATION_SCHEMA.COLUMNS where table_name = '%s' and column_name NOT IN ('rid');" % (from_table)
      self.conn.cursor.execute(selectTemplate)
      _datatable_attribute_types = self.conn.cursor.fetchall()
      # column name
      _attributes = [str(x[0]) for x in _datatable_attribute_types]
      # data type
      _attributes_type = [str(x[1]) for x in _datatable_attribute_types]
      return _attributes, _attributes_type



    def checkout_data_print(self, vlist, datatable, indextable, projection='*', where=None):
      if not self.check_table_exists(datatable):
            raise RelationNotExistError(datatable)
            return
      # user can only see everything except rid
      _attributes,_attributes_type = self.get_datatable_attribute(datatable)
      recordlist = self.select_records_of_version_list(vlist, indextable)
      if projection != '*':
        _attributes = projection.split(',')
      if where:
        sql = "SELECT %s FROM %s WHERE rid = ANY('%s'::int[]) AND %s;" % (",".join(_attributes), datatable, recordlist, "".join(where))
      else:
        sql = "SELECT %s FROM %s WHERE rid = ANY('%s'::int[]);" % (",".join(_attributes), datatable, recordlist)
      self.conn.cursor.execute(sql)
      #print sql
      return _attributes, self.conn.cursor.fetchall()

    def checkout_meta_print(self, versiontable, projection='*', where=None):
      if not self.check_table_exists(versiontable):
          raise RelationNotExistError(datatable)
          return
      _attributes,_attributes_type = self.get_datatable_attribute(versiontable)

      # TODO: need to change the where clause to match the corresponding type
      # for example, text -> 'text'
      version_type_map = {}
      for (a,b) in zip(_attributes, _attributes_type):
        version_type_map[a] = b

      if where:
        # where can be any type, need to interpreter
        try:
          where_type = version_type_map[where[0]] # the attribute to do select on
        except KeyError:
          raise ColumnNotExistError(where[0])
          return
        where_clause = where[0] + where[1] + "'%s'" % where[2] if where_type=='text' else "".join(where)
        sql = "SELECT %s from %s WHERE %s;" % (projection, versiontable, where_clause)
      else:
        sql = "SELECT %s from %s;" % (projection, versiontable)
      self.conn.cursor.execute(sql)
      #print sql
      return _attributes, self.conn.cursor.fetchall()

    # to_file needs an absolute path
    def checkout(self, vlist, datatable, indextable, to_table=None, to_file=None, delimiters=',', header=False, ignore=False):
        # sanity check
        if to_table:
          if RelationManager.reserve_table_check(to_table):
            raise ReservedRelationError(to_table)
            return
          if self.check_table_exists(to_table): # ask if user want to overwrite
              if ignore:
                self.drop_table_force(to_table)
              else:
                raise RelationOverwriteError(to_table)
                return

        if not self.check_table_exists(datatable):
            raise RelationNotExistError(datatable)
            return

        _attributes,_attributes_type = self.get_datatable_attribute(datatable)
        recordlist = self.select_records_of_version_list(vlist, indextable)
        #print recordlist
        if to_table:
          self.checkout_table(_attributes, recordlist, datatable, to_table, ignore)
        if to_file:
          self.checkout_file(_attributes, recordlist, datatable, to_file, delimiters, header)

        self.conn.connect.commit()

    def checkout_file(self, attributes, ridlist, datatable, to_file, delimiters, header):
        # convert to a tmp_table first
        self.drop_table_force('tmp_table')
        self.checkout_table(attributes, ridlist, datatable, 'tmp_table', None)
        sql = "COPY %s (%s) TO '%s' DELIMITER '%s' CSV HEADER;" if header else "COPY %s (%s) TO '%s' DELIMITER '%s' CSV;"
        sql = sql % ('tmp_table', ','.join(attributes), to_file, delimiters)
        self.conn.cursor.execute(sql)


    # Select the records into a new table
    def checkout_table(self, attributes, ridlist, datatable, to_table, ignore):
        if not ignore:
            sql = "SELECT %s INTO %s FROM %s WHERE rid = ANY('%s'::int[]);" \
              % (', '.join(attributes), to_table, datatable, ridlist)
        else:
            # TODO
            self.get_primary_key(datatable)
            sql = "SELECT %s INTO %s FROM %s WHERE rid = ANY('%s'::int[]);" \
                  % (', '.join(attributes), to_table, datatable, ridlist)
        #print sql
        self.conn.cursor.execute(sql)


    def drop_table(self, table_name):
        if not self.check_table_exists(table_name):
            raise RelationNotExistError(table_name)
            return
        drop_sql = "DROP TABLE %s" % table_name
        self.conn.cursor.execute(drop_sql)
        self.conn.connect.commit()


    def drop_table_force(self, table_name):
        if not self.check_table_exists(table_name):
          return
        drop_sql = "DROP TABLE %s" % table_name
        self.conn.cursor.execute(drop_sql)
        self.conn.connect.commit()

    def select_all_rid(self, table_name):
      select_sql = "SELECT rid from %s;" % table_name
      self.conn.cursor.execute(select_sql)
      return [x[0] for x in self.conn.cursor.fetchall()]

    def generate_complement_sql(self, table1, view_name, attributes=None):
      if not attributes:
        sql = "TABLE %s EXCEPT TABLE %s" % (table1, view_name)
      else:
        sql = "(SELECT %s from %s) EXCEPT (SELECT %s from %s)" % (','.join(attributes), table1, ','.join(attributes), view_name)
      return sql

    def create_parent_view(self, datatable, indextable, parent_vlist, view_name):
      plist = ",".join(parent_vlist)
      sql = "CREATE VIEW %s AS \
            SELECT * FROM %s INNER JOIN %s ON rid = ANY(rlist) \
          WHERE vid = ANY(ARRAY[%s]);" % (view_name, datatable, indextable, plist)
      self.conn.cursor.execute(sql)

    def drop_view(self, view_name):
      sql = "DROP VIEW IF EXISTS %s;" % view_name
      self.conn.cursor.execute(sql)

    def select_intersection_table(self, table1, view_name, join_attributes, projection='rid'):
      # SELECT rid FROM tmp_table INNER JOIN dataset1_datatable ON tmp_table.employee_id=dataset1_datatable.employee_id;
      join_clause = " AND ".join(["%s.%s=%s.%s" % (table1, attr, view_name, attr) for attr in join_attributes])
      sql = "SELECT %s.%s FROM %s INNER JOIN %s on %s;" % (view_name, projection, table1, view_name, join_clause)
      self.conn.cursor.execute(sql)
      return self.conn.cursor.fetchall()

    def convert_csv_to_table(self, file_path, destination_table, attributes, delimiters=',', header=False):
      sql = "COPY %s (%s) FROM '%s' DELIMITER '%s' CSV HEADER;" % (destination_table, ",".join(attributes), file_path, delimiters) if header \
          else "COPY %s (%s) FROM '%s' DELIMITER '%s' CSV;" % (destination_table, ",".join(attributes), file_path, delimiters)
      self.conn.cursor.execute(sql)
      self.conn.connect.commit()

    def create_relation(self,table_name):
      # Use CREATE SQL COMMAND
      print("create_relation: Under Construction.")

    # will drop existing table to create the new table
    def create_relation_force(self, table_name, sample_table, sample_table_attributes=None):
      if self.check_table_exists(table_name):
        self.drop_table(table_name)
      if not sample_table_attributes:
        sample_table_attributes,_ = self.get_datatable_attribute(sample_table)
      # sql = "CREATE TABLE %s ( like %s including all);" % (table_name, sample_table)

      # an easier approach to create empty table
      sql = "CREATE TABLE %s AS SELECT %s FROM %s WHERE 1=2;" % (table_name, ",".join(sample_table_attributes), sample_table)
      self.conn.cursor.execute(sql)
      self.conn.connect.commit()


    def check_table_exists(self,table_name):
      # SQL to check the exisistence of the table
      # print "checking if table %s exists" %(table_name)
      sql= "SELECT EXISTS (" \
           "SELECT 1 " \
           "FROM   information_schema.tables " \
           "WHERE  table_name = '%s');" % table_name
      # print sql
      self.conn.cursor.execute(sql)
      result = self.conn.cursor.fetchall()
      # print result[0][0]
      return result[0][0]

    def update_datatable(self, datatable_name, sql):
      _attributes, _attributes_type = self.get_datatable_attribute(datatable_name)
      sql = "INSERT INTO %s (%s) %s RETURNING rid;" % (datatable_name, ', '.join(_attributes), sql)
      self.conn.cursor.execute(sql)
      new_rids=[t[0] for t in self.conn.cursor.fetchall()]
      self.conn.connect.commit()
      # print new_rids
      return new_rids

    def clean(self):
      print("Clean: Under Construction.")#????

    @staticmethod
    def reserve_table_check(name):
        '''
        @summary: check if name is reserved
        @param name: name to be checked
        @result: return True if it is reserved
        '''
        # return name == 'datatable' or name == 'indextbl' or name == 'version' or name == 'tmp_table'
        return '_datatable' in name or '_indexTbl' in name or '_version' in name or 'orpheus' in name


    def select_records_of_version_list(self, vlist, indextable):
        targetv= ','.join(vlist)
        # sql = "SELECT distinct rlist FROM %s WHERE vlist && (ARRAY[%s]);" % (indextable, targetv)
        sql = "SELECT distinct rlist FROM %s WHERE vid = ANY(ARRAY[%s]);" % (indextable, targetv)
        self.conn.cursor.execute(sql)
        data = [','.join(map(str,x[0])) for x in self.conn.cursor.fetchall()]
        # data
        return '{' + ','.join(data) + '}'

    def get_primary_key(self,tablename): #this method return nothing, what you want?
        sql="SELECT a.attname, format_type(a.atttypid, a.atttypmod) AS data_type FROM   pg_index i " \
            "JOIN   pg_attribute a ON a.attrelid = i.indrelid " \
            "AND a.attnum = ANY(i.indkey)" \
            "WHERE  i.indrelid = '%s'::regclass " \
            "AND    i.indisprimary;"%tablename
        self.conn.cursor.execute(sql)
        #print tablename+'\'s primary key'
        #print self.conn.cursor.fetchall()

    def get_number_of_rows(self,tablename):
        sql = "SELECT COUNT (*) from %s" % tablename
        self.conn.cursor.execute(sql)
        result = self.conn.cursor.fetchall()
        # print result
        return result[0][0]