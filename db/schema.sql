
\prompt 'What is your full name?: ' MASJID_ADMIN_NAME
\prompt 'What is your email address?: ' MASJID_ADMIN_EMAIL

SET client_min_messages TO WARNING;


DROP TABLE IF EXISTS forgot_message;
DROP TABLE IF EXISTS team_member_auth_token;
DROP TABLE IF EXISTS team_member;

DROP TYPE IF EXISTS t_auth_type CASCADE;
DROP TYPE IF EXISTS t_sex CASCADE;
DROP TYPE IF EXISTS EMAILTAG CASCADE;


CREATE TYPE t_auth_type AS ENUM ('web', 'iOS', 'android');
CREATE TYPE t_sex AS ENUM ('M', 'F');
CREATE TYPE EMAILTAG AS ENUM(
      'login_verification'
    , 'welcome'
    , 'forgot'
    );


CREATE TABLE team_member (
	  id SERIAL UNIQUE PRIMARY KEY NOT NULL
    , email VARCHAR(256) NOT NULL
    , password char(60) NOT NULL
    , admin BOOLEAN NOT NULL DEFAULT FALSE
    , name VARCHAR(256) NOT NULL
    , read_only BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX i_team_member_email on team_member(email);


CREATE TABLE team_member_auth_token (
      id SERIAL UNIQUE PRIMARY KEY NOT NULL
    , team_member_id INT NOT NULL REFERENCES team_member (id)
    , token char(60) NOT NULL UNIQUE
    , auth_type t_auth_type NOT NULL
    , last_use_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT statement_timestamp()
);
CREATE INDEX i_team_member_auth_token_token ON team_member_auth_token(token);


CREATE TABLE person (
	  id SERIAL UNIQUE PRIMARY KEY NOT NULL
    , name VARCHAR(256) NOT NULL
    , date_of_birth DATE NOT NULL
    , sex t_sex NOT NULL
    , street1 VARCHAR(255) NOT NULL
    , street2 VARCHAR(255) NULL
    , city VARCHAR(255) NOT NULL
    , state CHAR(2) NOT NULL
    , zip CHAR(5) NOT NULL
    , zip_plus4 char(4) NULL
    , phone_number VARCHAR(32) NULL
    , email VARCHAR(256) NULL
);



CREATE TABLE forgot_message (
      id SERIAL UNIQUE PRIMARY KEY NOT NULL
    , guid CHAR(36)
    , team_member_id INT NULL REFERENCES team_member(id)
    , date_sent TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT statement_timestamp()
    , date_validated TIMESTAMP WITH TIME ZONE NULL
);
CREATE INDEX i_forgot_message_guid ON Forgot_message(guid);




CREATE TYPE t_signin_type AS ENUM ('web', 'iOS', 'android', 'in_person');
CREATE TABLE covid_signin_sheet
(
      "id" SERIAL UNIQUE PRIMARY KEY NOT NULL
    , dt timestamp with time zone not null
    , name bytea NOT NULL
    , phone bytea NOT NULL
    , email bytea not null
);

CREATE TABLE covid_qrcodes
(
      "id" SERIAL UNIQUE PRIMARY KEY NOT NULL
    , dt timestamp with time zone not null default statement_timestamp()
    , name bytea NOT NULL
    , phone bytea NOT NULL
    , email bytea not null
);




CREATE OR REPLACE function random_string(length INTEGER) RETURNS TEXT AS
$$
declare
  chars TEXT[] := '{0,1,2,3,4,5,6,7,8,9,B,C,D,F,G,H,J,K,L,M,N,P,Q,R,S,T,V,W,X,Z,b,c,d,f,g,h,j,k,l,m,n,p,q,r,s,t,v,w,x,z}';
  result TEXT := '';
  i INTEGER := 0;
begin
  IF length < 0 THEN
    RAISE exception 'Given length cannot be less than 0';
  END IF;
  FOR i IN 1..length LOOP
    result := result || chars[1+random()*(array_length(chars, 1)-1)];
  END LOOP;
  RETURN result;
END;
$$ LANGUAGE plpgsql;


CREATE or replace function f_covid_signin(
    p_dt timestamp with time zone
  , p_name varchar
  , p_phone varchar
  , p_email varchar
  , p_key varchar
) returns text as $$
BEGIN
        INSERT INTO covid_signin_sheet(dt
    , name
    , phone
    , email
    )
    values (p_dt
    , pgp_sym_encrypt(p_name, p_key)
    , pgp_sym_encrypt(p_phone, p_key)
    , pgp_sym_encrypt(p_email, p_key)
    );
    return '1';
end;
    $$ LANGUAGE plpgsql;


CREATE or replace function f_covid_signin_update(
    p_id integer
  , p_name varchar
  , p_phone varchar
  , p_email varchar
  , p_key varchar
) returns text as $$
BEGIN
        UPDATE covid_signin_sheet set
         name = pgp_sym_encrypt(p_name, p_key)
         , phone =  pgp_sym_encrypt(p_phone, p_key)
         , email = pgp_sym_encrypt(p_email, p_key)
         where id = p_id
    );
    return '1';
end;
    $$ LANGUAGE plpgsql;




-- -- **********************************************************************************************
-- -- **********************************************************************************************
-- -- Login
-- --
-- -- This function IS FOR the initial login
-- -- Returns a row WITH a token OR 0 rows
CREATE OR REPLACE FUNCTION f_logIn (p_email VARCHAR, p_password VARCHAR, p_auth_type t_auth_type) RETURNS
        TABLE (token VARCHAR
               , login_id INT
               , name VARCHAR
               , admin BOOLEAN
               , read_only BOOLEAN
               ) AS $$
DECLARE
  token VARCHAR := '';
  arow RECORD;
  crypted_token VARCHAR;
BEGIN
  SELECT t.id, t.name, t.admin, t.read_only INTO arow
  FROM team_member t
  WHERE email = p_email
  AND password=crypt(p_password, password);
  IF NOT FOUND THEN
    RETURN;
  END IF;
  -- successful login
  SELECT gen_random_uuid() INTO token;
  SELECT crypt(token, gen_salt('bf')) INTO crypted_token;
  INSERT INTO team_member_auth_token (team_member_id, token, auth_type) VALUES (arow.id, crypted_token, p_auth_type);
  RETURN QUERY SELECT token, arow.id, arow.name, arow.admin, arow.read_only;
END;
$$ LANGUAGE plpgsql;

-- -- This function IS FOR subsequent logins WITH every request
-- -- RETURNS (adminId, adminName) OR
CREATE OR REPLACE FUNCTION f_auth(p_token VARCHAR) RETURNS TABLE (id INT, name VARCHAR) AS $$
DECLARE
    arow RECORD;
BEGIN
    SELECT team_member_id INTO arow FROM team_member_auth_token WHERE token = crypt(p_token, token);
    IF NOT FOUND THEN
        RETURN;
    END IF;
    -- we're good
    -- update last update
    UPDATE team_member_auth_token SET last_use_date = statement_timestamp() WHERE token = p_token;
    RETURN QUERY SELECT p.id, p.name FROM team_member p WHERE p.id = arow.team_member_id;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION f_logout(p_token VARCHAR) RETURNS INT AS $$
BEGIN
    DELETE FROM team_member_auth_token WHERE token = crypt(p_token, token);
    RETURN 1;
END;
$$ LANGUAGE plpgsql;


-- -- **********************************************************************************************
-- -- **********************************************************************************************
-- -- Forgot Password
-- --

-- -- RETURNS guid (token) that goes INTO email OR no rows IF the email does not exist
CREATE OR REPLACE FUNCTION f_forgot (p_email VARCHAR) RETURNS TABLE (guid VARCHAR) AS $$
DECLARE
  guid VARCHAR := '';
  arow RECORD;
  v_team_member_id INTEGER;
BEGIN
  SELECT p.id INTO v_team_member_id FROM team_member p WHERE p.email = p_email;
  IF NOT FOUND THEN
    RETURN;
  END IF;
  SELECT gen_random_uuid() INTO guid;
  DELETE FROM forgot_message f WHERE f.team_member_id = v_team_member_id;
  INSERT INTO forgot_message(guid, team_member_id) VALUES (guid, v_team_member_id);
  RETURN QUERY SELECT guid;
END;
$$ LANGUAGE plpgsql;


-- -- IF you click on forgot your password it will log you off existing sessions
CREATE OR REPLACE FUNCTION f_change_password_forgot(p_guid VARCHAR,  p_password VARCHAR) RETURNS TABLE (team_member_id INT, email VARCHAR) AS $$
DECLARE
  v_email varchar := '';
  v_team_member_id INTEGER;
BEGIN
  SELECT forgot_message.team_member_id INTO v_team_member_id FROM forgot_message WHERE guid = p_guid AND date_validated IS NULL;
  IF NOT FOUND THEN
    RETURN;
  END IF;
  SELECT team_member.email INTO v_email FROM team_member WHERE id = v_team_member_id;
  DELETE FROM team_member_auth_token WHERE team_member_auth_token.team_member_id = v_team_member_id;
  UPDATE team_member SET password = crypt(p_password, gen_salt('bf', 10)) WHERE id = v_team_member_id;
  UPDATE forgot_message SET date_validated = statement_timestamp() WHERE guid = p_guid;
  RETURN QUERY SELECT v_team_member_id, v_email;
END;
$$ LANGUAGE plpgsql;





-- -- **********************************************************************************************
-- -- **********************************************************************************************
-- -- Change Password
-- --

-- don't delete all tokens when you change the password
CREATE OR REPLACE FUNCTION f_change_password(p_team_member_id INT,  p_old_password VARCHAR, p_new_password VARCHAR) RETURNS TABLE (result INT) AS $$
DECLARE
  arow RECORD;
  v_email_id INTEGER;
  v_team_member_id INTEGER;
BEGIN
  PERFORM id FROM team_member WHERE id = p_team_member_id AND password=crypt(p_old_password, password);
  IF NOT FOUND THEN
    RETURN;
  END IF;
  UPDATE team_member SET password = crypt(p_new_password, gen_salt('bf', 10)) WHERE id = p_team_member_id;
  RETURN QUERY SELECT 1;
END;
$$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION f_add_team_member(
p_email TEXT
, p_admin BOOLEAN
, p_name text
, p_read_only BOOLEAN
)
returns table (guid text) as $$
    BEGIN
        insert into team_member(
                        email
                      , password
                      , admin
                      , name
                      , read_only)
                      values (
                                p_email
                              , ''
                              , p_admin
                              , p_name
                              , p_read_only
                             );
        RETURN QUERY SELECT * FROM f_forgot(p_email);

    end;
    $$ LANGUAGE plpgsql;


insert into team_member(
                        email
                      , password
                      , admin
                      , name
                      , read_only)
                      values (
                              :'MASJID_ADMIN_EMAIL'
                              , ''
                              , true
                              , :'MASJID_ADMIN_NAME'
                              , false
                             );



CREATE FUNCTION install_print_guid_message(p_email TEXT)
RETURNS text AS
$$
DECLARE
  output  text;
BEGIN

PERFORM * FROM f_forgot(p_email);
UPDATE forgot_message set guid = random_string(8);

select into output 
chr(10)
|| chr(10)
|| 'This is your password recovery code: ' || guid 
|| chr(10)
|| chr(10)
|| 'Please save this so that you can set your password.         '
|| chr(10)
|| chr(10)
|| chr(10)
from forgot_message limit 1;
  /* Return the output text variable. */
  RETURN output;
END
$$ LANGUAGE plpgsql;

SET client_min_messages TO NOTICE;

SELECT install_print_guid_message as "Installation Message" from install_print_guid_message(:'MASJID_ADMIN_EMAIL');

