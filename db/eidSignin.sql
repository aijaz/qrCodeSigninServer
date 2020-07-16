DROP TABLE IF EXISTS event_slot;
DROP table if exists reservation;
drop table if exists event;


CREATE TABLE event
(
      "id" SERIAL UNIQUE PRIMARY KEY NOT NULL
    , dt timestamp with time zone not null
    , name TEXT NOT NULL
);

create table reservation
(
    id text not null unique primary key
    , reservation_dt timestamp with time zone not null
    , name bytea NOT NULL
    , phone bytea NOT NULL
    , email bytea not null

);

CREATE TABLE event_slot
(
      event_id int not null references event(id)
    , slot_id int not null
    , reservation_id text null references reservation(id)
    , primary key (event_id, slot_id)
);
CREATE index i_event_slot_reservation on event_slot(reservation_id);


CREATE or replace function f_create_event(
    p_dt timestamp with time zone
  , p_name varchar
) returns int as $$
DECLARE
    r_id INTEGER;
BEGIN
        INSERT INTO event(dt, name)
        values (p_dt, p_name)
        returning id into r_id;
    return r_id;
end;
    $$ LANGUAGE plpgsql;


CREATE or replace function f_add_slots(
    p_event_id integer
  , p_num_slots integer
) returns int as $$
DECLARE
    max_id INTEGER;
BEGIN
    select coalesce(max(slot_id), 0) into max_id from event_slot where event_id = p_event_id;

    with slot_ids(gen_slot_id) as (select * from generate_series(max_id + 1, max_id + p_num_slots))
         insert into event_slot(
                                event_id
                                , slot_id
                                )
            select p_event_id
                 , gen_slot_id
            from slot_ids;
    return p_num_slots;
end;
    $$ LANGUAGE plpgsql;




CREATE OR REPLACE FUNCTION f_unused_reservation_id() RETURNS TEXT AS $$
DECLARE
    slug TEXT;
BEGIN
    LOOP
        SELECT random_string(6) INTO slug;
        PERFORM id FROM reservation r WHERE id = slug;
        IF NOT FOUND THEN
            RETURN slug;
        END IF;
    END LOOP;
END;
$$ LANGUAGE plpgsql;


CREATE TYPE t_reservation_result_type AS ENUM (
    'success'
    , 'too_many_slots_requested'
    , 'not_enough_slots_available'
    );

CREATE or replace function f_reserve_slots(
    p_event_id integer
  , p_num_slots integer
  , p_name varchar
  , p_phone varchar
  , p_email varchar
  , p_key varchar
  , p_max_slots_reservable integer
) returns table(result t_reservation_result_type, reservation_id text) as $$
DECLARE
    num_slots_available INTEGER;
    v_reservation_id text;
    next_available_slot_id INTEGER;
BEGIN

    -- lock table

    LOCK TABLE event_slot in ACCESS EXCLUSIVE MODE ;

    SELECT COUNT(*)
    INTO num_slots_available
    from event_slot
    where event_slot.event_id = p_event_id
      and event_slot.reservation_id is null;

    IF p_max_slots_reservable < p_num_slots THEN
        return QUERY SELECT 'too_many_slots_requested'::t_reservation_result_type, null;
        return;
    END IF;

    IF num_slots_available < p_num_slots THEN
        return QUERY SELECT 'not_enough_slots_available'::t_reservation_result_type, null;
        return;
    END IF;

    -- make sure random string isn't in database
    select f_unused_reservation_id() into v_reservation_id;

    -- create reservation
        INSERT INTO reservation(id
    , reservation_dt
    , name
    , phone
    , email
    )
    values (v_reservation_id
    , current_timestamp
    , pgp_sym_encrypt(p_name, p_key)
    , pgp_sym_encrypt(p_phone, p_key)
    , pgp_sym_encrypt(p_email, p_key)
    );


    with cte(id) as (
        select event_slot.slot_id from event_slot
        where event_slot.event_id = p_event_id
          and event_slot.reservation_id is null
        order by event_slot.slot_id limit p_num_slots)
    update event_slot set reservation_id = v_reservation_id
    FROM cte
    where event_slot.event_id = p_event_id
    and event_slot.slot_id = cte.id;

    return query select 'success'::t_reservation_result_type, v_reservation_id;

end;
    $$ LANGUAGE plpgsql;

create or replace function f_available_slots_report() returns table (event_id integer, slots_available bigint) as $$
    BEGIN
        return query
            select s.event_id
                 , count(*) as slots_available
            from event_slot s
            where reservation_id is null
            group by s.event_id
            order by s.event_id;
    end;
    $$ LANGUAGE plpgsql;

-- create or replace function f_release_expired_event_slot_holds() returns void as $$
--     BEGIN
--     update event_slot set reservation_id = null, hold_until_dt = null
--     where hold_until_dt < current_timestamp;
-- end;
--     $$ LANGUAGE plpgsql;



--   , p_num_minutes_expiration integer
--                  , current_timestamp + make_interval(mins := p_num_minutes_expiration)
