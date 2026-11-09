import pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'scripts'))
from sources import extract,mentions
from build_index import candidates
VID='aircAruvnKk'
class SourceTests(unittest.TestCase):
 def record(self,raw):return {'_id':'source1','userId':'author1','postedAt':'2026-11-09T12:00:00.000Z','title':'A public post','slug':'a-public-post','contents':{'html':raw},'user':{'displayName':'Author'}}
 def test_post_body_link_has_post_attribution(self):
  row=mentions(self.record('<p>A useful lecture: <a href="https://youtu.be/'+VID+'">Neural networks</a></p>'),'post')[0]
  self.assertEqual(row['vid'],VID);self.assertEqual(row['source_type'],'post');self.assertEqual(row['author_id'],'author1');self.assertNotIn('commentId=',row['url']);self.assertEqual(row['link_title'],'Neural networks')
 def test_bare_embedded_video_with_no_comment_text_is_kept(self):
  rows=mentions(self.record('<iframe src="https://www.youtube.com/embed/'+VID+'"></iframe>'),'comment');self.assertEqual(len(rows),1)
 def test_duplicate_links_count_once_per_source(self):
  rows=mentions(self.record('<p>https://youtu.be/'+VID+' https://www.youtube.com/watch?v='+VID+'</p>'),'post');self.assertEqual(len(rows),1)
 def test_escaped_and_encoded_urls(self):
  for url in ['https://www.youtube.com/watch?feature=share&amp;v='+VID,'https%3A%2F%2Fyoutu.be%2F'+VID,'https://www.youtube-nocookie.com/embed/'+VID]:self.assertIn(VID,extract('<p>'+url+'</p>'))
 def test_owner_exclusion_survives_rebuilds(self):
  self.assertNotIn('dQw4w9WgXcQ',candidates([{'vid':'dQw4w9WgXcQ'}]))
 def test_single_author_single_month_is_eligible(self):
  record=mentions(self.record('<p>https://youtu.be/'+VID+'</p>'),'post')[0];self.assertEqual(list(candidates([record])),[VID])
 def test_distinct_source_types_are_preserved(self):
  raw='<p>https://youtu.be/'+VID+'</p>';rows=mentions(self.record(raw),'post')+mentions(self.record(raw),'comment');self.assertEqual({r['source_type'] for r in candidates(rows)[VID]},{'post','comment'})

class PaginationTests(unittest.TestCase):
 def test_short_nonempty_page_does_not_end_scan(self):
  import tempfile,contextlib,io,unittest.mock as mock
  import ingest
  rows=[{'_id':'p1','postedAt':'2000-10-01T12:00:00.000Z','contents':{'html':''}},{'_id':'p2','postedAt':'2000-09-01T12:00:00.000Z','contents':{'html':''}}]
  pages=[{'posts':{'results':rows}},{'posts':{'results':[{'_id':'p3','postedAt':'2000-02-01T12:00:00.000Z','contents':{'html':''}}]}},{'posts':{'results':[]}}]
  with tempfile.TemporaryDirectory() as tmp, mock.patch.object(ingest,'CACHE',pathlib.Path(tmp)), mock.patch.object(ingest,'gql',side_effect=pages) as query, mock.patch.object(ingest.time,'sleep'), contextlib.redirect_stdout(io.StringIO()):
   result=ingest.scan(('post',2000))
  self.assertEqual(query.call_count,3);self.assertEqual(result['scanned'],3);self.assertTrue(result['exhausted'])

 def test_inclusive_final_boundary_is_deduplicated_and_exhausted(self):
  import tempfile,contextlib,io,unittest.mock as mock
  import ingest
  row={'_id':'p1','postedAt':'2000-10-01T12:00:00.000Z','contents':{'html':''}}
  pages=[{'posts':{'results':[row]}},{'posts':{'results':[row]}},{'posts':{'results':[]}}]
  with tempfile.TemporaryDirectory() as tmp, mock.patch.object(ingest,'CACHE',pathlib.Path(tmp)), mock.patch.object(ingest,'gql',side_effect=pages) as query, mock.patch.object(ingest.time,'sleep'), contextlib.redirect_stdout(io.StringIO()):
   result=ingest.scan(('post',2000))
  self.assertEqual(query.call_count,3);self.assertEqual(result['scanned'],1);self.assertTrue(result['exhausted'])

if __name__=='__main__':unittest.main()
