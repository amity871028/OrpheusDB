# OrpheusDB
[OrpheusDB][orpheus] is a hosted system that supports _dataset version management_. OrpheusDB is built on top of standard relational databases, thus it inherits much of the same benefits of relational databases, while also compactly storing, tracking, and recreating versions
on demand.

OrpheusDB is a multi-year project, supported by the National Science Foundation via award number XXX. It shares the vision of the vision paper on the [DataHub][datahub] project in supporting collaborative data analytics.


<!-- OrpheusDB is an open-sourced database that enable data version capability on relational database system.This repository is an implementation of ongoing research under the project OrpheusDB at the University of Illinois at Urbana Champaign led by [Prof. Aditya Parameswaran][prof]. -->


### Version
The current version is 1.0.0.

### Features
OrpheusDB is built using [PostgreSQL][postgressite] and [Click][clicksite], a command line tool written in Python. Our current version supports advanced querying capabilities, using both the SQL queries and the git-style version control commands. 

Users can operate on collaborative versioned datasets (CVD) much like they would with source code version control. The _checkout_ command allows users to materialize one or more specific versions of a CVD as a newly created regular table within a relational database or as a csv file; the _commit_ command allows users to add a new version to CVD by making the local changes made by the user on their materialized table or on their exported csv file visible to others. Other commands we support are _init_, _create\_user_, _config_, _whoami_, _ls_, _db_, _drop_, and _optimize_.

Users can also input SQL queries on CVD via the command line using the _run_ command. It allows users to directly execute SQL queries on one or more versions of a dataset without table materialization. Moreover, it allows users to apply  aggregation functions grouped by version ids or identify versions that satisfy some property. <!-- TODO: UPDATE/INSERT/REMOVE -->

### Key Design Innovations
* OrpheusDB is built on top of a traditional relational database, thus it inherits all of the benefits in the relational database systems "for free"
* OrpheusDB supports advanced querying and versioning capabilities, via both the SQL queries and the git-style version control commands.
* OrpheusDB has powerful data model and partition optimization algorithm for providing efficient version control performance over large-scaled datasets. 


### System Requirement
Prior to install OrpheusDB locally,  users need to make sure that the following software are setup successfully: 
* Python 2.7.x
* PostgreSQL >= 9.5

### Installation Instructions
OrpheusDB comes with standard `setup.py` script for installation. The required python dependency packages include
* click >= 6.6
* psycopy2 >= 2.6.2
* pandas >= 0.19.0
* pyyaml >= 3.12
* pyparsing >=2.1.1

Users are able to install any of missing dependencies themselves via `pip`. Alternatively, an easier way to install all dependencies is through `pip install .`

After installation, users can use `dh --help` to list all the available commands in OrpheusDB. By default, `dh` is the alias for OrpheusDB user interface.

<!--
```
pip install .
dh --help
```
-->

### Configuration
OrpheusDB needs to know where is the underlying relational database storage before execution. To specify such, change the corresponding fields in `config.yaml`.

### Dataset Version Control in OrpheusDB
The fundamental unit of storage within OrpheusDB is a collaborative versioned dataset (CVD) to which one or more users can contribute. Each CVD corresponds to a relation with a fixed schema, and implicitly contains many versions of that relation. There is a many-to-many relationship between records in the relation and versions that is captured within the CVD: each record can belong to many versions, and each version can contain many records. Each version has a unique version id, vid, and each record has its unique record id, rid. The record ids are used to identify immutable records within the CVD and are not visible to end-users of OrpheusDB.

<!-- Collaborative Version Dataset is the unit of operation in OrpheusDB. Each CVD stores dataset and its version information. Each version is represented with an unique version vid, _vid_. -->

### User Tutorials
To start with, user can create an OrpheusDB username with a password via the `create_user` command. Upon finishing, it will be pushed to the underlying data storage with SUPERUSER privilege. Command `config` is to login through created user and `whoami` is to check the current user name that is currently logged in. 

Please note here that OrpheusDB provides the most basic implementation for user information, i.e. there is no password protection. However, this feature is subject to change in future version.
```
dh create_user
dh config
dh whoami
```

The `init` command provides ways to load file (currently a csv file) into OrpheusDB (as a CVD), with the all records as its first version. To let OrpheusDB know what is the schema for this dataset, user can provide a sample schema file through option `-s`. Each line in the schema file has the following format `<attribute name>, <type of the attribute>`. In this example, `data.csv` file contains 3 attributes, namely `age`, `employee_id` and `salary`.

<!-- In the current release, only `csv` file format is supported in the `init`. -->

```
dh init data.csv dataset1 -s sample_schema.csv
```

User can checkout one or more desired versions through the `checkout` command, to either a csv file or a structured table in RDMS. <!-- Again, only `csv` format is supported. --> In this example, it checkouts the version 1 of CVD dataset1 as a csv file named checkout.csv. 
```
dh checkout dataset1 -v 1 -f checkout.csv
```
Any changed or new records from commit file will be appended to the corresponding CVD, labeled with a new version. One special case is the committing of a subset of previous checkedout version. For such case, OrpheusDB will commit as user wishes.

After changes are made to the previous checkout versions, OrpheusDB can commit these changes to its corresponding CVD assuming unchanged schema. 

In this example, it commits the modified checkout.csv back to CVD dataset1. Note here since OrpheusDB internally logged the CVD that checkout.csv was checked out from, there is no need to specify the CVD name in the `commit` command. 
```
dh commit -f checkout.csv -m 'first commit'
```

To avoid the cost of additional storage, OrpheusDB also supports query against CVD. The run command will prompt user with input to execute SQL command directly. If `-f` is specified, it will execute the SQL file specified.  
```
dh run
```

OrpheusDB supports a richer syntax of SQL statements. During the execution, OrpheusDB will detect keywords like `CVD` so it knows the query is against CVD. In this example, OrpheusDB will select the `age` column from CVD dataset1 whose version id is equal to either `1` or `2`.
```
SELECT age FROM VERSION 1,2 OF CVD dataset1
```

If version number is unknown, OrpheusDB also supports query against it. The follow statement will select those version numbers that any records reside in match the where constraint. It is worth noticing that the `GROUP BY` clause is required to aggregate on versions.

In this example, OrpheusDB selects all the versions that have one or more records whose age equals to 25.
```
SELECT vid FROM CVD dataset1 WHERE age = 25 GROUP BY vid
```

### Todos
 - ~~db run~~
 - ~~change user password settings~~
 - tracker overwrite, get rid of the old mapping
 - change cvd to public schema
 - update meta after dropping dataset
 - update load current state path from .meta/config
 - $ORPHEUS_HOME$ in bashrc
 - verbose mode
 - mock testing
 
License
----

MIT

[//]: # (These are reference links used in the body of this note and get stripped out when the markdown processor does its job. There is no need to format nicely because it shouldn't be seen. Thanks SO - http://stackoverflow.com/questions/4823468/store-comments-in-markdown-syntax)

   [prof]: http://web.engr.illinois.edu/~adityagp/#
   [clicksite]: http://click.pocoo.org/5/
   [orpheus]: http://orpheus-db.github.io/
   [datahub]: https://arxiv.org/abs/1409.0798
   [postgressite]: https://www.postgresql.org/
