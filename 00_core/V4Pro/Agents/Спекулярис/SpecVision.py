import bpy
import json

def apply_pose_from_json(filepath):
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    armature = bpy.data.objects['Armature']  # имя твоей арматуры
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='POSE')
    
    pose = data['pose']
    
    # Поворот головы
    bone = armature.pose.bones.get('head')
    if bone and 'rotation' in pose['head']:
        rot = pose['head']['rotation']
        bone.rotation_euler = (rot[0], rot[1], rot[2])
    
    # Взгляд (можно через поворот глаз или отдельные кости)
    if 'gaze' in pose:
        # логика для глаз
        pass
    
    bpy.ops.object.mode_set(mode='OBJECT')

# Использование
apply_pose_from_json('C:/path/to/pose.json')