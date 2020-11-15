import click

@click.group()
def main():
    pass


@main.command()
@click.argument('bom-file', type=click.File('rb'))
def parse_bom(bom_file):
    print("works!")


if __name__ == '__main__':
    main(prog_name='python -m eva-3d')
