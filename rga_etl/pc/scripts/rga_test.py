from rga_etl.databases.utils import init_session, init_instrument
from rga_etl.pc.rga import init_rga


def main():
    Session = init_session()
    with Session() as session:
        init_instrument(session)

    rga = init_rga()
    if not rga.check_head_online():
        raise RuntimeError("RGA head is not online.")
    print(f"The ID of the RGA is {rga.check_id()}.\n")
    print("The status of the RGA is:")
    print(f"{rga.get_status()}.")
    rga.filament.turn_off()
    rga.disconnect()


if __name__ == "__main__":
    main()
