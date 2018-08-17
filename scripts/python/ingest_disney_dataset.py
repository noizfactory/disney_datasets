# -*- coding: utf-8 -*-
"""ingest_disney_dataset.py is an attempt at ingesting the Disney dataset.

The script imports the model files and traverses the hierarchy and other
json files to rebuild it in Maya. Post that the script exports the recreated
hierarchy as an alembic file. We will later use this alembic file in gaffer
and try to rebuild the shader assignments and the set assmebly there using
optimisations like instancing.

Variables:
    root_dir {str} -- Path to the root of the model directory
    asset {str} -- The current model being iterated
    asset_dir {str} -- Path to the current model directory
    asset_obj {str} -- Path to the current model obj file
    asset_hier {str} -- Path to the current model hierarchy json file
    with open(asset_hier, 'r') as hier_json: {json object} -- Json object of
    the model hierarchy json file
    for model, hier in hier_data.iteritems(): {tuple} -- Model and its
    hierarchy tuple pair from the hierrahcy json object
"""
import json
import os
import glob

import pymel.core as pm


def get_asset_objs(obj_dir):
    """Return list of all objs in the asset obj directory.

    This finds all the .obj files for an asset in its directory along-with
    the .obj files in the archives directory.

    Arguments:
        obj_dir {str} -- Root level "obj" directory in the Disney dataset.

    Returns:
        list -- List of all obj files in the dataset obj directory.
    """
    obj_files = []
    assets = os.listdir(obj_dir)
    for asset in assets:
        asset_dir = os.path.join(obj_dir, asset)
        archive_dir = os.path.join(asset_dir, 'archives')
        asset_objs = glob.glob(os.path.join(asset_dir, '*.obj'))
        archive_objs = glob.glob(os.path.join(archive_dir, '*.obj'))
        obj_files += sorted(asset_objs + archive_objs)

    return obj_files


def import_asset_obj(obj_file):

    """Import the .obj file for the asset.

    Arguments:
        obj_file {[type]} -- [description]

    Returns:
        str -- Path of the obj file that was imported
    """
    pm.newFile(f=True)
    pm.importFile(obj_file, type='OBJ', ignoreVersion=True,
                  mergeNamespacesOnClash=False, rpr='',
                  options='mo=1;lo=0', pr=True)

    return obj_file


def rebuild_asset_hierarchy(obj_file):
    """Rebuild the asset hierarchy in Maya based on the .hier file.

    The disney dataset provides a .hier json file which contains the asset
    hierarchy. We use this to rebuild it in Maya so that we can export it
    later into alembic with the same hierarchy.

    Arguments:
        obj_file {str} -- Path to the imported obj file.

    Returns:
        PyNode -- PyNode object of the import model.
    """
    hier_json = obj_file.replace('.obj', '.hier')
    with open(hier_json, 'r') as asset_hier:
        hier_data = json.load(asset_hier)

    for model, hier in hier_data.iteritems():
        hier_split = hier.split('|')
        hier_split.pop(0)
        model_par = hier_split[-1]
        root_par = hier_split[0]
        for index, hier_elem in reversed(list(enumerate(hier_split))):
            if index != 0:
                elem_par = hier_split[index - 1]
                try:
                    hier_elem_node = pm.PyNode(hier_elem)
                except Exception:
                    hier_elem_node = pm.createNode('transform', n=hier_elem)
                try:
                    elem_par_node = pm.PyNode(elem_par)
                except Exception:
                    elem_par_node = pm.createNode('transform', n=elem_par)
                hier_elem_node.setParent(elem_par_node)
        try:
            model_node = pm.PyNode(model)
            model_par_node = pm.PyNode(model_par)
            model_node.setParent(model_par_node)
        except Exception:
            print 'Model is missing! First import it into your scene.'
            model_node = None
        root_par_node = pm.PyNode(root_par)

    return root_par_node


def export_asset_abc(obj_file, root_node):
    """Export the obj hierarchy from Maya as alembic.

    We export the rebuilt model hierarchy as alembic so that we can use it
    in any other DCC like gaffer.

    Arguments:
        obj_file {str} -- Path to the imported and rebuilt obj file.
        root_node {PyNode} -- PyNode object of the top root node of the model.

    Returns:
        str -- Path of the exported abc file.
    """
    obj_dir = os.path.dirname(obj_file)
    obj_name = os.path.basename(obj_file)
    abc_dir = obj_dir.replace('obj', 'abc')
    abc_name = obj_name.replace('.obj', '.abc')
    abc_file = os.path.join(abc_dir, abc_name)

    if not os.path.exists(abc_dir):
        os.makedirs(abc_dir)

    pm.select(root_node)
    root_node_name = root_node.fullPath()

    abc_args = ['-frameRange 1 1', '-uvWrite', '-worldSpace', '-writeUVSets',
                '-dataFormat ogawa', '-root ' + root_node_name,
                '-file ' + abc_file]
    abc_arg = ' '.join(abc_args)
    pm.AbcExport(j=abc_arg)

    return abc_file


# # Test
root_dir = '/home/sshrestha/workspace/library/disney_datasets/island'
obj_dir = os.path.join(root_dir, 'obj')
obj_files = get_asset_objs(obj_dir)
for obj_file in obj_files:
    import_asset_obj(obj_file)
    root_node = rebuild_asset_hierarchy(obj_file)
    abc_file = export_asset_abc(obj_file, root_node)
    print 'Rebuilt and exported abc file to', abc_file
