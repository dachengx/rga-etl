from rga_etl.utils import init_session
from rga_etl.rga import init_rga


def main():
    Session = init_session()
    with Session() as session:
        instrument = init_instrument(session)

    rga = init_rga()
    if not rga.check_head_online():
        raise RuntimeError("RGA head is not online.")
    print(f"The ID of the RGA is {rga.check_id()}.\n")
    print(f"The status of the RGA is {rga.get_status()}.")
    rga.filament.turn_off()
    rga.disconnect()


if __name__ == "__main__":
    main()
