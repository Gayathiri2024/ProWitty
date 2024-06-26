from llama_index.core import SimpleDirectoryReader
from llama_index.readers.file import CSVReader

from llama_index.core.node_parser import SentenceSplitter
import chromadb
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core import StorageContext
from llama_index.core import VectorStoreIndex
from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.core.storage.chat_store import SimpleChatStore

from utils import write_transcript_file
from aws_service import aws_embed
from utils import write_transcript_file

class RawData:
    def __init__(
            self, 
            rawFileStorageDirectory: str = "storage/files", 
            videoFileName: str = "ProWitty_presentation.mp4",
            withTranscription: bool = False
        ):
        self.rawFileStorageDirectory = rawFileStorageDirectory
        self.videoFileName = videoFileName

        if withTranscription:
            write_transcript_file(
                fileDirectory = rawFileStorageDirectory + "/videos/" + videoFileName 
            )
            
    def get_nodes(self):
        
        # Writing a text file which stores the transcript of the video file.
        # This process should carried before running the reader.
        # write_transcript_file(
        #     write_transcript_file = self.rawFileStorageDirectory + "/videos/" + self.videoFileName
        # )

        # Reading the files inside the directory,
        # And preparing the document out of it.
        reader = SimpleDirectoryReader(input_dir = self.rawFileStorageDirectory, recursive = False)

        documents = []
        for docs in reader.iter_data():
            documents.extend(docs)

        # Splitting the document into nodes.
        splitter = SentenceSplitter(chunk_size = 256, chunk_overlap = 48)
        nodes = splitter.get_nodes_from_documents(documents)

        # Returning the nodes
        return nodes
    
class DataPipeline:
    def __init__(
            self, 
            rawFileStorageDirectory: str = "storage/files", 
            videoFileName: str = "",
            withTranscription: bool = False
        ):
        self.nodes = RawData(
            rawFileStorageDirectory = rawFileStorageDirectory,
            videoFileName = videoFileName,
            withTranscription = withTranscription
        ).get_nodes()
        self.embedModel = aws_embed()
    
    def build_and_save(self):
        db = chromadb.PersistentClient(path = "storage/vectorDB")
        chromaCollection = db.get_or_create_collection(name = "defaultDB")
        vectorStore = ChromaVectorStore(chroma_collection = chromaCollection)
        storageContext = StorageContext.from_defaults(vector_store = vectorStore)

        VectorStoreIndex(
            nodes = self.nodes,
            embed_model = self.embedModel,
            storage_context = storageContext
        )

        chatStore = SimpleChatStore()
        chatStore.add_message("user01", message= ChatMessage(
                    role=MessageRole.USER,
                    content=f"Hello assistant, we are having a insightful discussion about our project"))
        chatStore.add_message("user01", message= ChatMessage(
                    role=MessageRole.ASSISTANT, 
                    content="Okay, sounds good."))
        chatStore.persist(persist_path = "storage/chat_store.json") 

        # return self.nodes

if __name__ == "__main__":
    dp = DataPipeline(
        rawFileStorageDirectory = "storage/files",
        videoFileName = "ProWitty_presentation.mp4",
        withTranscription = True
    )

    dp.build_and_save()