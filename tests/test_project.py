import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import subprocess
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server


class ProjectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        server.DATA = server.ROOT/'_deploy'/'test-runs'/uuid.uuid4().hex

    def setUp(self):
        self.pid = server.uid()
        self.p = {'id':self.pid,'schema':1,'revision':1,'source':'unchanged.mp4',
                  'media':{'duration':10,'audio':True},'clips':[
                      {'id':'a','start':1.,'end':3.,'enabled':True,'locked':True,'label':'Kept'},
                      {'id':'b','start':6.,'end':8.,'enabled':True,'locked':False,'label':'Other'}],
                  'graphics':[],'notes':[],'name':'Test'}
        server.write(server.folder(self.pid)/'project.json',self.p)
        server.write(server.folder(self.pid)/'revisions'/'00001.json',self.p)

    def test_export_never_overwrites_existing_file(self):
        location=server.folder(self.pid)
        source=location/'render.mp4';source.write_bytes(b'new render')
        existing=location/'video.mp4';existing.write_bytes(b'original')
        delivered=server.save_export(source,location,'video.mp4')
        self.assertEqual(existing.read_bytes(),b'original')
        self.assertEqual(delivered.name,'video (2).mp4')
        self.assertEqual(delivered.read_bytes(),source.read_bytes())

    def test_export_filename_rejects_path(self):
        for name in ['../video.mp4','/video.mp4','folder\\video.mp4','']:
            with self.assertRaises(ValueError):server.export_filename(name)

    def test_native_picker_cancel_keeps_preferences(self):
        with patch('server.subprocess.run', return_value=subprocess.CompletedProcess([],0,'','')):
            self.assertEqual(server.choose_export_folder(), {'cancelled':True})
        self.assertFalse(server.PICKER_LOCK.locked())

    def test_native_picker_returns_selected_folder(self):
        location=server.folder(self.pid)
        with patch('server.subprocess.run', return_value=subprocess.CompletedProcess([],0,str(location)+'\n','')):
            self.assertEqual(server.choose_export_folder()['directory'],str(location))

    def test_native_picker_timeout_releases_lock(self):
        with patch('server.subprocess.run', side_effect=subprocess.TimeoutExpired('picker',600)):
            with self.assertRaisesRegex(ValueError,'timed out'):server.choose_export_folder()
        self.assertFalse(server.PICKER_LOCK.locked())

    def test_locked_boundary_rejected_for_ai(self):
        incoming=copy.deepcopy(self.p)
        incoming['clips'][0]['end']=2.5
        with self.assertRaisesRegex(ValueError,'locked'):
            server.save(self.pid,incoming,actor='ai')
        self.assertEqual(server.project(self.pid),self.p)

    def test_locked_removal_rejected_for_ai(self):
        incoming=copy.deepcopy(self.p)
        incoming['clips'].pop(0)
        with self.assertRaisesRegex(ValueError,'locked'):
            server.save(self.pid,incoming,actor='ai')

    def test_human_trim_and_history_are_recoverable(self):
        incoming=copy.deepcopy(self.p)
        incoming['clips'][0]['start']=.5
        saved=server.save(self.pid,incoming)
        self.assertEqual(saved['revision'],2)
        self.assertEqual(server.read(server.folder(self.pid)/'revisions'/'00001.json'),self.p)
        self.assertEqual(saved['source'],'unchanged.mp4')

    def test_stale_save_rejected(self):
        server.save(self.pid,self.p)
        with self.assertRaisesRegex(ValueError,'changed elsewhere'):
            server.save(self.pid,self.p)

    def test_ai_can_change_unlocked_clip(self):
        incoming=copy.deepcopy(self.p)
        incoming['clips'][1]['end']=9.
        self.assertEqual(server.save(self.pid,incoming,actor='ai')['clips'][1]['end'],9.)

    def test_invalid_source_bounds(self):
        for start,end in [(-1,3),(1,11),(3,3),(1,float('nan'))]:
            p=copy.deepcopy(self.p);p['clips'][0].update(start=start,end=end)
            with self.assertRaises(ValueError):server.validate(p)

    def test_restore_does_not_overwrite_source(self):
        incoming=copy.deepcopy(self.p);incoming['source']='replacement.mp4'
        self.assertEqual(server.save(self.pid,incoming)['source'],'unchanged.mp4')

    def test_excluded_clip_not_counted(self):
        self.p['clips'][1]['enabled']=False
        self.assertEqual(server.duration(self.p),2.)

    def test_graphics_must_fit_edited_duration(self):
        self.p['graphics']=[{'id':'g','type':'title','start':3,'end':5,'text':'Test'}]
        with self.assertRaisesRegex(ValueError,'Graphic timing'):
            server.validate(self.p)

    def test_project_path_is_scoped(self):
        with self.assertRaises(ValueError):server.folder('../outside')

    def test_imported_ids_cannot_inject_markup(self):
        self.p['clips'][0]['id']='x\" onclick=\"alert(1)'
        with self.assertRaisesRegex(ValueError,'Invalid clip ID'):
            server.validate(self.p)

    def finished(self):
        p=copy.deepcopy(self.p)
        p['rendered']={'path':'finished.mp4','media':{'duration':4,'audio':True},'mapping':[
            {'sourceStart':1.,'sourceEnd':3.,'editStart':0.},
            {'sourceStart':6.,'sourceEnd':8.,'editStart':2.}]}
        return p

    def test_finished_graphics_and_audio_are_used(self):
        parts=server.playback(self.finished())
        self.assertEqual([(c['path'],c['start'],c['end']) for c in parts],
                         [('finished.mp4',0.,2.),('finished.mp4',2.,4.)])

    def test_trim_keeps_finished_media_mapping(self):
        p=self.finished();p['clips'][0]['start']=1.25
        parts=server.playback(p)
        self.assertEqual(parts[0]['start'],.25)
        self.assertEqual(parts[1]['out'],1.75)

    def test_extended_edge_restores_only_missing_raw(self):
        p=self.finished();p['clips'][0]['end']=3.2
        parts=server.playback(p)
        self.assertEqual([c['kind'] for c in parts],['edit','source','edit'])
        self.assertAlmostEqual(parts[1]['start'],3.)
        self.assertAlmostEqual(parts[1]['end'],3.2)
        self.assertAlmostEqual(parts[2]['out'],2.2)

    def test_restored_interval_can_span_raw_and_edit(self):
        p=self.finished();p['clips']=[{'id':'r','start':2.,'end':7.,'enabled':True}]
        parts=server.playback(p)
        self.assertEqual([c['kind'] for c in parts],['edit','source','edit'])
        self.assertEqual([(c['start'],c['end']) for c in parts],[(1.,2.),(3.,6.),(2.,3.)])
        self.assertEqual(sum(c['end']-c['start'] for c in parts),5.)


if __name__=='__main__':unittest.main()
