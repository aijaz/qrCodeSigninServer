\set QUIET 1
\set VERBOSITY terse
\timing off
SET client_min_messages TO WARNING;

drop database if exists signindb;
drop user if exists signin;

create user signin with password 'dbpass' createdb;
create database signindb with owner signin;
\c signindb
create extension pgcrypto;
\c - signin

\i schema.sql