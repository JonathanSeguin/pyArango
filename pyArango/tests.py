import unittest, copy

from connection import *
from database import *
from collection import *
from document import *
from query import *
from theExceptions import *

class ArangocityTests(unittest.TestCase):

	def setUp(self):
		self.conn = Connection()

		try :
			self.conn.createDatabase(name = "test_db")
		except CreationError :
			pass

		self.db = self.conn["test_db"]
		self._resetUp()

	def _resetUp(self) :
		self.db.update()
		for colName in self.db.collections :
			if not self.db[colName].isSystem :
				self.db[colName].delete()

	def tearDown(self):
		self._resetUp()
		
	def createManyUsers(self, nbUsers) :
	 	collection = self.db.createCollection(name = "users")
		for i in xrange(nbUsers) :
			doc = collection.createDocument()
			doc["name"] = "Tesla-%d" % i
			doc["number"] = i
			doc["species"] = "human"
			doc.save()
		return collection
	
	def test_collection_create_delete(self) :
		col = self.db.createCollection(name = "to_be_erased")
		self.db["to_be_erased"].delete()

		self.assertRaises(DeletionError, self.db["to_be_erased"].delete)
	
	def test_collection_count_truncate(self) :
		collection = self.db.createCollection(name = "lala")	
		collection.truncate()
		doc = collection.createDocument()
		doc.save()
		doc2 = collection.createDocument()
		doc2.save()
		self.assertEqual(2, collection.count())
		collection.truncate()
		self.assertEqual(0, collection.count())

	def test_document_create_update_delete(self) :
		collection = self.db.createCollection(name = "lala")
		doc = collection.createDocument()
		doc["name"] = "Tesla"
		self.assertTrue(doc.URL is None)
		doc.save()
		self.assertTrue(doc.URL is not None)
		url = copy.copy(doc.URL)
		doc["name"] = "Tesla2"
		doc.save()
		self.assertEqual(doc.URL, url)
		doc.delete()
		self.assertTrue(doc.URL is None)
	
	def test_document_fetch_by_key(self) :
		collection = self.db.createCollection(name = "lala")
		doc = collection.createDocument()
		doc["name"] = 'iop'
		doc.save()
		doc2 = collection.fetchDocument(doc._key)
		self.assertEqual(doc._id, doc2._id)

	def test_document_create_patch(self) :
		collection = self.db.createCollection(name = "lala")
		doc = collection.createDocument()
		doc["name"] = "Tesla3"
		self.assertRaises(ValueError, doc.patch)
		doc.save()
		doc.patch()
	
	def test_aql_validation(self) :
	 	collection = self.db.createCollection(name = "users")
		doc = collection.createDocument()
		doc["name"] = "Tesla"
		doc.save()

		aql = "FOR c IN users FILTER c.name == @name LIMIT 2 RETURN c.name"
		bindVars = {'name' : 'Tesla-3'}

	def test_aql_query_rawResults_true(self) :
		self.createManyUsers(100)
		
		aql = "FOR c IN users FILTER c.name == @name LIMIT 10 RETURN c.name"
		bindVars = {'name' : 'Tesla-3'}
		q = self.db.AQLQuery(aql, rawResults = True, batchSize = 10, bindVars = bindVars)
		self.assertEqual(len(q.result), 1)
		self.assertEqual(q[0], 'Tesla-3')

	def test_aql_query_rawResults_false(self) :
		self.createManyUsers(100)

		aql = "FOR c IN users FILTER c.name == @name LIMIT 10 RETURN c"
		bindVars = {'name' : 'Tesla-3'}
		q = self.db.AQLQuery(aql, rawResults = False, batchSize = 10, bindVars = bindVars)
		self.assertEqual(len(q.result), 1)
		self.assertEqual(q[0]['name'], 'Tesla-3')		
		self.assertTrue(isinstance(q[0], Document))		
	
	def test_aql_query_batch(self) :
		nbUsers = 100
		self.createManyUsers(nbUsers)
		
		aql = "FOR c IN users LIMIT %s RETURN c" % nbUsers
		q = self.db.AQLQuery(aql, rawResults = False, batchSize = 1, count = True)
		lstRes = []
		for i in xrange(nbUsers) :
			lstRes.append(q[0]["number"])
			try :
				q.nextBatch()
			except StopIteration :
				self.assertEqual(i, nbUsers-1)
		
		lstRes.sort()
		self.assertEqual(lstRes, range(nbUsers))
		self.assertEqual(q.count, nbUsers)

	def test_simple_query_example_batch(self) :
		nbUsers = 100
		col = self.createManyUsers(nbUsers)
		
		example = {'species' : "human"}

		q = col.fetchByExample(example, batchSize = 1, count = True)
		lstRes = []
		for i in xrange(nbUsers) :	
			lstRes.append(q[0]["number"])
			try :
				q.nextBatch()
			except StopIteration :
				self.assertEqual(i, nbUsers-1)
		
		lstRes.sort()
		self.assertEqual(lstRes, range(nbUsers))
		self.assertEqual(q.count, nbUsers)

	def test_simple_query_all_batch(self) :
		nbUsers = 100
		col = self.createManyUsers(nbUsers)
		
		q = col.fetchAll(batchSize = 1, count = True)
		lstRes = []
		for i in xrange(nbUsers) :	
			lstRes.append(q[0]["number"])
			try :
				q.nextBatch()
			except StopIteration :
				self.assertEqual(i, nbUsers-1)
		
		lstRes.sort()
		self.assertEqual(lstRes, range(nbUsers))
		self.assertEqual(q.count, nbUsers)

	def test_empty_query(self) :
		col = self.createManyUsers(1)
		example = {'species' : "rat"}
		q = col.fetchByExample(example, batchSize = 1, count = True)
		self.assertEqual(q.result, [])
	
	def test_cursor(self) :
		nbUsers = 2
		col = self.createManyUsers(nbUsers)
		
		q = col.fetchAll(batchSize = 1, count = True)
		q2 = Cursor(q.database, q.cursor.id, rawResults = True)

		lstRes = [q.result[0]["number"], q2.result[0]["number"]]
		lstRes.sort()
		self.assertEqual(lstRes, range(nbUsers))
		self.assertEqual(q.count, nbUsers)

	def test_fields_on_set(self) :
		def strFct(v) :
			import types
			return type(v) is types.StringType	

		class Col_on_set(Collection) :
			_validation = {
				"on_save" : False,
				"on_set" : True,
				"allow_foreign_fields" : False
			}
			
			_fields = {
				"str" : Field(constraintFct = strFct),
				"notNull" : Field(notNull = True)
			}
			
		myCol = self.db.createCollection('Col_on_set')
		doc = myCol.createDocument()
		self.assertRaises(ConstraintViolation, doc.__setitem__, 'str', 3)
		self.assertRaises(ConstraintViolation, doc.__setitem__, 'notNull', None)
		self.assertRaises(SchemaViolation, doc.__setitem__, 'foreigner', None)

	def test_fields_on_save(self) :
		def strFct(v) :
			import types
			return type(v) is types.StringType	

		class Col_on_set(Collection) :

			_validation = {
				"on_save" : True,
				"on_set" : False,
				"allow_foreign_fields" : False
			}

			_fields = {
				"str" : Field(constraintFct = strFct),
				"notNull" : Field(notNull = True)
			}
			
		myCol = self.db.createCollection('Col_on_set')
		doc = myCol.createDocument()
		doc["str"] = 3
		self.assertRaises(ValidationError, doc.save)
		doc["str"] = "string"
		doc["foreigner"] = "string"
		self.assertRaises(ValidationError,  doc.save)	

	def test_document_cache(self) :
		class DummyDoc(object) :
			def __init__(self, key) :
				self.key = key
			def __repr__(self) :
				return repr(self.key)

		docs = []
		for i in xrange(10) :
			docs.append(DummyDoc(i))

		cache = DocumentCache(5)
		for doc in docs :
			cache.cache(doc)
			self.assertEqual(cache.head.key, doc.key)
		
		self.assertEqual(cache.cacheStore.keys(), [5, 6, 7, 8, 9])	
		self.assertEqual(cache.getChain(), [9, 8, 7, 6, 5])
		doc = cache[5]
		self.assertEqual(cache.head.key, doc.key)
		self.assertEqual(cache.getChain(), [5, 9, 8, 7, 6])

	def test_validation_default_settings(self) :

		class Col_empty(Collection) :
			pass

		class Col_empty2(Collection) :
			_validation = {
				"on_save" : False,
			}

		c = Col_empty
		self.assertEqual(c._validation, Collection_metaclass._validationDefault)

		c = Col_empty2
		self.assertEqual(c._validation, Collection_metaclass._validationDefault)

	def test_validation_default_inlavid_key(self) :

		def keyTest() :
			class Col(Collection) :
				_validation = {
					"on_sav" : True,
				}

		self.assertRaises(KeyError, keyTest)
		
	def test_validation_default_inlavid_value(self) :

		def keyTest() :
			class Col(Collection) :
				_validation = {
					"on_save" : "wrong",
				}

		self.assertRaises(ValueError, keyTest)
	
	def test_collection_type_creation(self) :
		class Edgy(Edges) :
			pass
		
		class Coly(Collection) :
			pass

		edgy = self.db.createCollection("Edgy")
		self.assertEqual(edgy.type, COLLECTION_EDGE_TYPE)
		coly = self.db.createCollection("Coly")
		self.assertEqual(coly.type, COLLECTION_DOCUMENT_TYPE)

	def test_save_edge(self) :
		class Human(Collection) :
			_fields = {
				"name" : Field()
			}

		class Relation(Edges) :
			_fields = {
				"ctype" : Field()
			}

		humans = self.db.createCollection("Human")
		rels = self.db.createCollection("Relation")

		tete = humans.createDocument()
		tete["name"] = "tete"
		tete.save()
		toto = humans.createDocument()
		toto["name"] = "toto"
		toto.save()

		link = rels.createEdge()
		link["ctype"] = "brother"
		link.links(tete, toto)

		sameLink = rels[link._key]
		self.assertEqual(sameLink["ctype"], link["ctype"])
		self.assertEqual(sameLink._from, tete._id)
		self.assertEqual(sameLink._to, toto._id)

	def test_get_edge(self) :
		class Human(Collection) :
			_fields = {
				"number" : Field()
			}

		class Relation(Edges) :
			_fields = {
				"number" : Field()
			}

		humans = self.db.createCollection("Human")
		rels = self.db.createCollection("Relation")
		humansList = []
		
		for i in range(10) :
			h = humans.createDocument()
			h["number"] = i
			humansList.append(h)
			h.save()

		for i in range(10) :
			e = rels.createEdge()
			e["number"] = i
			if i % 2 == 1 :
				e.links(humansList[0], humansList[i])
			else :
				e.links(humansList[-1], humansList[i])

		outs = humansList[0].getOutEdges(rels)
		self.assertEqual(len(outs), 5)
		for o in outs :
			self.assertEqual(o["number"] % 2, 1)

		ins = humansList[-1].getOutEdges(rels)
		self.assertEqual(len(ins), 5)
		for i in ins :
			self.assertEqual(i["number"] % 2, 0)

if __name__ == "__main__" :
	unittest.main()