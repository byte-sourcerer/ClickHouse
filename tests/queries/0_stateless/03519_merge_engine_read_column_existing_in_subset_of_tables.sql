set enable_analyzer=1;

drop table if exists test1;
drop table if exists test2;
drop table if exists test3;
drop table if exists test_merge;

create table test1(a UInt64, b UInt64) engine=Memory;
create table test2(a UInt64, c UInt64) engine=Memory;
create table test3(a UInt64, d UInt64) engine=Memory;
create table test_merge (a UInt64, b UInt64, c UInt64, d UInt64, e UInt64) engine=Merge(database(), 'test');

insert into test1 select 1, 2;
insert into test2 select 3, 4;
insert into test3 select 5, 6;

select 'a';
select a from test_merge order by all;
select 'b';
select b from test_merge order by all;
select 'c';
select c from test_merge order by all;
select 'd';
select d from test_merge order by all;
select 'e';
select e from test_merge order by all;
select 'a, b';
select a, b from test_merge order by all;
select 'a, c';
select a, c from test_merge order by all;
select 'a, d';
select a, d from test_merge order by all;
select 'a, e';
select a, e from test_merge order by all;
select 'b, c';
select b, c from test_merge order by all;
select 'b, d';
select b, d from test_merge order by all;
select 'b, e';
select b, e from test_merge order by all;
select 'c, d';
select c, d from test_merge order by all;
select 'c, e';
select c, e from test_merge order by all;
select 'a, b, c';
select a, b, c from test_merge order by all;
select 'a, b, d';
select a, b, d from test_merge order by all;
select 'a, b, e';
select a, b, e from test_merge order by all;
select 'a, c, d';
select a, c, d from test_merge order by all;
select 'a, c, e';
select a, c, e from test_merge order by all;
select 'b, c, d';
select b, c, d from test_merge order by all;
select 'b, c, e';
select b, c, e from test_merge order by all;
select 'c, d, e';
select c, d, e from test_merge order by all;
select 'b, _table';
select b, _table from test_merge order by all;
select 'c, _table';
select c, _table from test_merge order by all;
select 'd, _table';
select d, _table from test_merge order by all;
select 'e, _table';
select e, _table from test_merge order by all;
select 'b, c, _table';
select b, c, _table from test_merge order by all;
select 'b, d, _table';
select b, d, _table from test_merge order by all;
select 'b, e, _table';
select b, e, _table from test_merge order by all;
select 'c, d, _table';
select c, d, _table from test_merge order by all;
select 'c, e, _table';
select c, e, _table from test_merge order by all;
select 'd, e, _table';
select d, e, _table from test_merge order by all;

drop table test1;
drop table test2;
drop table test3;
drop table test_merge;

