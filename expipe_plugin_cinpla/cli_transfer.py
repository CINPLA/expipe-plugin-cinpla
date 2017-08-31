from .ssh_tools import get_login, login, ssh_execute, untar
from . import action_tools
from .imports import *


def attach_to_cli(cli):
    @cli.command('copy-to-config', short_help='Copy file to expipe config directory')
    @click.argument('filename', type=click.Path(exists=True))
    def copy_to_config(filename):
        shutil.copy(filename, expipe.config.config_dir)

    @cli.command('transfer', short_help='Transfer a dataset related to an expipe action.')
    @click.argument('action-id', type=click.STRING)
    @click.option('--to-local',
                  is_flag=True,
                  help='Transfer action data from server to local directory.',
                  )
    @click.option('--from-local',
                  is_flag=True,
                  help='Transfer action data from local directory to server.',
                  )
    @click.option('--no-trash',
                  is_flag=True,
                  help='Do not send local data to trash after transfer.',
                  )
    @click.option('--overwrite',
                  is_flag=True,
                  help='Overwrite data or not.',
                  )
    @click.option('-r', '--recursive',
                  is_flag=True,
                  help='Recursive directory transfer.',
                  )
    @click.option('-e', '--exclude',
                  multiple=True,
                  type=click.Choice(action_tools.nwb_main_groups),
                  help='Omit raw data, acquisition etc..',
                  )
    @click.option('-i', '--include',
                  multiple=True,
                  type=click.Choice(action_tools.nwb_main_groups),
                  help='Only select which folders to include.',
                  )
    @click.option('--port',
                  default=22,
                  type=click.INT,
                  help='SSH port. Default is 22',
                  )
    @click.option('--hostname',
                  type=click.STRING,
                  help='SSH hostname.',
                  )
    @click.option('--username',
                  type=click.STRING,
                  help='SSH username.',
                  )
    @click.option('--server',
                  default='norstore',
                  type=click.STRING,
                  help='Name of server as named in config.yaml. Default is "norstore"',
                  )
    def transfer(action_id, to_local, from_local, overwrite, no_trash,
                 exclude, include, port, username,
                 hostname, recursive, server):
        assert server in expipe.config.settings
        server_dict = expipe.config.settings.get(server)
        if len(exclude) > 0 and len(include) > 0:
            raise IOError('You can only use exlude or include')
        project = expipe.get_project(PAR.USER_PARAMS['project_id'])
        action = project.require_action(action_id)
        fr = action.require_filerecord()

        host, user, pas, port = get_login(hostname=hostname,
                                          username=username,
                                          port=port,
                                          server=server_dict)
        ssh, scp_client, sftp_client, pbar = login(hostname=host,
                                                   username=user,
                                                   password=pas, port=port)
        serverpath = expipe.config.settings[server]['data_path']
        server_data = os.path.dirname(os.path.join(serverpath, fr.exdir_path))
        server_data = server_data.replace('\\', '/')
        if to_local:
            local_data = os.path.dirname(action_tools._get_local_path(fr, make=True))
            if recursive:
                scp_client.get(server_data, local_data, recursive=True)
                try:
                    pbar[0].close()
                except Exception:
                    pass
            else:
                if overwrite:
                    shutil.rmtree(local_data)
                    os.mkdir(local_data)
                print('Initializing transfer of "' + server_data + '" to "' +
                      local_data + '"')
                print('Packing tar archive')
                exclude_statement = " "
                for ex in exclude:
                    exclude_statement += '--exclude=' + ex + ' '
                if len(include) > 0:
                    for ex in action_tools.nwb_main_groups:
                        if ex not in include:
                            exclude_statement += '--exclude=' + ex + ' '
                ssh_execute(ssh, "tar" + exclude_statement + "-cf " +
                            server_data + '.tar ' + server_data)
                scp_client.get(server_data + '.tar', local_data + '.tar',
                               recursive=False)
                try:
                    pbar[0].close()
                except Exception:
                    pass
                print('Unpacking tar archive')
                untar(local_data + '.tar', server_data) # TODO merge with existing
                print('Deleting tar archives')
                os.remove(local_data + '.tar')
                sftp_client.remove(server_data + '.tar')
        elif from_local:
            local_data = os.path.dirname(action_tools._get_local_path(fr, assert_exists=True))
            if recursive:
                scp_client.get(server_data, local_data, recursive=True)
                try:
                    pbar[0].close()
                except Exception:
                    pass
            else:
                print('Initializing transfer of "' + local_data + '" to "' +
                      server_data + '"')
                try: # make directory for untaring
                    sftp_client.mkdir(server_data)
                except IOError:
                    pass
                if len(exclude) > 0 or len(include) > 0:
                    raise NotImplementedError
                print('Packing tar archive')
                shutil.make_archive(local_data, 'tar', local_data)
                scp_client.put(local_data + '.tar', server_data + '.tar',
                               recursive=False)
                try:
                    pbar[0].close()
                except Exception:
                    pass
                print('Unpacking tar archive')
                cmd = "tar -C " + server_data + " -xf " + server_data + '.tar'
                if not overwrite:
                    cmd += " -k --skip-old-files"
                else:
                    cmd += " -k --overwrite"
                ssh_execute(ssh, cmd)
                print('Deleting tar archives')
                sftp_client.remove(server_data + '.tar')
                os.remove(local_data + '.tar')
            if not no_trash:
                try:
                    from send2trash import send2trash
                    send2trash(local_data)
                    print('local data "' + local_data +
                          '" sent to trash.')
                except Exception:
                    warnings.warn('Unable to send local data to trash')

        else:
            raise IOError('You must choose "to-local" or "from-local"')
            ssh.close()
        sftp_client.close()
        scp_client.close()
        # TODO send to trash

    @cli.command('copy-action', short_help='Copy a dataset related to an expipe action')
    @click.argument('action-id', type=click.STRING)
    @click.option('--overwrite',
                  is_flag=True,
                  help='Overwrite modules or not.',
                  )
    @click.option('--to-local',
                  is_flag=True,
                  help='',
                  )
    @click.option('--from-local',
                  is_flag=True,
                  help='Transfer action data from local directory to server.',
                  )
    @click.option('--move',
                  is_flag=True,
                  help='Delete source.',
                  )
    @click.option('--exclude',
                  type=click.Choice(['acquisition', 'analysis', 'processing',
                                     'epochs', 'none']),
                  default='none',
                  help='Omit raw data, acquisition etc..',
                  )
    def copy_action(action_id, to_local, from_local, overwrite, exclude, move):
        project = expipe.get_project(PAR.USER_PARAMS['project_id'])
        action = project.require_action(action_id)
        fr = action.require_filerecord()
        if to_local:
            source = fr.server_path
            dest = action_tools._get_local_path(fr)
        elif from_local:
            dest = fr.server_path
            source = action_tools._get_local_path(fr)
        else:
            raise IOError('You must choose "to-local" or "from-local"')
        print('Copying "' + source + '" to "' + dest + '"')
        if not os.path.exists(source):
            raise FileExistsError('Source file does not exist')
        if os.path.exists(dest):
            if overwrite:
                shutil.rmtree(dest)
            else:
                raise FileExistsError('Destination "' + dest +
                                      '" exist, use overwrite flag')
        if exclude != 'none':
            print('Ignoring "' + exclude + '"')

        def exclude_dir(src, names):
            if src.endswith('main.exdir') and exclude != 'none':
                return [exclude]
            else:
                return set()

        shutil.copytree(source, dest, ignore=exclude_dir)
        if move:
            shutil.rmtree(source)
