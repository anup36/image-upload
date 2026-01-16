import { useState, useEffect } from "react";
import axios from "axios";
import { Upload, Filter, X, Download, Trash2, Calendar, Tag, User, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Gallery = () => {
  const [images, setImages] = useState([]);
  const [filteredImages, setFilteredImages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [filterOpen, setFilterOpen] = useState(false);
  const [viewerOpen, setViewerOpen] = useState(false);
  const [selectedImage, setSelectedImage] = useState(null);
  const [dragOver, setDragOver] = useState(false);

  // Upload form state
  const [file, setFile] = useState(null);
  const [uploader, setUploader] = useState("");
  const [tags, setTags] = useState("");
  const [description, setDescription] = useState("");
  const [uploading, setUploading] = useState(false);

  // Filter state
  const [filterUploader, setFilterUploader] = useState("");
  const [filterTags, setFilterTags] = useState("");
  const [filterDateFrom, setFilterDateFrom] = useState("");
  const [filterDateTo, setFilterDateTo] = useState("");

  useEffect(() => {
    fetchImages();
  }, []);

  const fetchImages = async (filters = {}) => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filters.uploader) params.append('uploader', filters.uploader);
      if (filters.tags) params.append('tags', filters.tags);
      if (filters.date_from) params.append('date_from', filters.date_from);
      if (filters.date_to) params.append('date_to', filters.date_to);

      const response = await axios.get(`${API}/images?${params.toString()}`);
      setImages(response.data);
      setFilteredImages(response.data);
    } catch (error) {
      console.error("Failed to fetch images:", error);
      toast.error("Failed to load gallery");
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file || !uploader) {
      toast.error("Please select a file and enter your name");
      return;
    }

    setUploading(true);
    const formData = new FormData();
    formData.append("file", file);
    formData.append("uploader", uploader);
    formData.append("tags", tags);
    if (description) formData.append("description", description);

    try {
      await axios.post(`${API}/images/upload`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      toast.success("Image uploaded successfully!");
      setUploadOpen(false);
      setFile(null);
      setUploader("");
      setTags("");
      setDescription("");
      fetchImages();
    } catch (error) {
      console.error("Upload failed:", error);
      toast.error(error.response?.data?.detail || "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile && droppedFile.type.startsWith("image/")) {
      setFile(droppedFile);
    } else {
      toast.error("Please drop an image file");
    }
  };

  const handleDelete = async (imageId) => {
    if (!window.confirm("Are you sure you want to delete this image?")) return;

    try {
      await axios.delete(`${API}/images/${imageId}`);
      toast.success("Image deleted successfully");
      fetchImages();
      setViewerOpen(false);
    } catch (error) {
      console.error("Delete failed:", error);
      toast.error("Failed to delete image");
    }
  };

  const handleDownload = async (image) => {
    try {
      const response = await axios.get(`${BACKEND_URL}${image.url}`, {
        responseType: "blob",
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", image.filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      toast.success("Download started");
    } catch (error) {
      console.error("Download failed:", error);
      toast.error("Failed to download image");
    }
  };

  const applyFilters = () => {
    const filters = {};
    if (filterUploader) filters.uploader = filterUploader;
    if (filterTags) filters.tags = filterTags;
    if (filterDateFrom) filters.date_from = new Date(filterDateFrom).toISOString();
    if (filterDateTo) filters.date_to = new Date(filterDateTo).toISOString();
    fetchImages(filters);
    setFilterOpen(false);
    toast.success("Filters applied");
  };

  const clearFilters = () => {
    setFilterUploader("");
    setFilterTags("");
    setFilterDateFrom("");
    setFilterDateTo("");
    fetchImages();
    toast.success("Filters cleared");
  };

  return (
    <div className="min-h-screen bg-white">
      {/* Header */}
      <header className="border-b border-border bg-white sticky top-0 z-10 backdrop-blur-xl bg-white/80">
        <div className="max-w-[1800px] mx-auto px-6 md:px-12 lg:px-20 py-8">
          <div className="flex items-center justify-between">
            <h1 className="text-5xl md:text-7xl font-serif tracking-tight leading-none" data-testid="gallery-title">
              Lumina Gallery
            </h1>
            <div className="flex items-center gap-4">
              <Dialog open={filterOpen} onOpenChange={setFilterOpen}>
                <DialogTrigger asChild>
                  <Button variant="outline" size="lg" className="rounded-full" data-testid="filter-button">
                    <Filter className="w-5 h-5 mr-2" />
                    Filters
                  </Button>
                </DialogTrigger>
                <DialogContent className="sm:max-w-[500px]" data-testid="filter-dialog">
                  <DialogHeader>
                    <DialogTitle className="font-serif text-3xl">Filter Gallery</DialogTitle>
                  </DialogHeader>
                  <div className="space-y-6 py-4">
                    <div>
                      <Label className="flex items-center gap-2 mb-2">
                        <User className="w-4 h-4" />
                        Uploader Name
                      </Label>
                      <Input
                        placeholder="Enter uploader name"
                        value={filterUploader}
                        onChange={(e) => setFilterUploader(e.target.value)}
                        data-testid="filter-uploader-input"
                      />
                    </div>
                    <div>
                      <Label className="flex items-center gap-2 mb-2">
                        <Tag className="w-4 h-4" />
                        Tags (comma-separated)
                      </Label>
                      <Input
                        placeholder="nature, landscape, urban"
                        value={filterTags}
                        onChange={(e) => setFilterTags(e.target.value)}
                        data-testid="filter-tags-input"
                      />
                    </div>
                    <div>
                      <Label className="flex items-center gap-2 mb-2">
                        <Calendar className="w-4 h-4" />
                        Date From
                      </Label>
                      <Input
                        type="date"
                        value={filterDateFrom}
                        onChange={(e) => setFilterDateFrom(e.target.value)}
                        data-testid="filter-date-from-input"
                      />
                    </div>
                    <div>
                      <Label className="flex items-center gap-2 mb-2">
                        <Calendar className="w-4 h-4" />
                        Date To
                      </Label>
                      <Input
                        type="date"
                        value={filterDateTo}
                        onChange={(e) => setFilterDateTo(e.target.value)}
                        data-testid="filter-date-to-input"
                      />
                    </div>
                    <div className="flex gap-3 pt-4">
                      <Button onClick={applyFilters} className="flex-1 rounded-full" data-testid="apply-filters-button">
                        Apply Filters
                      </Button>
                      <Button onClick={clearFilters} variant="outline" className="flex-1 rounded-full" data-testid="clear-filters-button">
                        Clear All
                      </Button>
                    </div>
                  </div>
                </DialogContent>
              </Dialog>

              <Dialog open={uploadOpen} onOpenChange={setUploadOpen}>
                <DialogTrigger asChild>
                  <Button size="lg" className="rounded-full shadow-lg hover:shadow-xl" data-testid="upload-button">
                    <Upload className="w-5 h-5 mr-2" />
                    Upload Image
                  </Button>
                </DialogTrigger>
                <DialogContent className="sm:max-w-[600px]" data-testid="upload-dialog">
                  <DialogHeader>
                    <DialogTitle className="font-serif text-3xl">Upload to Gallery</DialogTitle>
                  </DialogHeader>
                  <form onSubmit={handleUpload} className="space-y-6 py-4">
                    <div
                      className={`upload-dropzone p-12 rounded-sm text-center cursor-pointer ${dragOver ? 'drag-over' : ''}`}
                      onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                      onDragLeave={() => setDragOver(false)}
                      onDrop={handleDrop}
                      onClick={() => document.getElementById('file-input').click()}
                      data-testid="upload-dropzone"
                    >
                      <Upload className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
                      {file ? (
                        <p className="font-medium">{file.name}</p>
                      ) : (
                        <>
                          <p className="font-medium mb-2">Drag & drop an image</p>
                          <p className="text-sm text-muted-foreground">or click to browse</p>
                        </>
                      )}
                    </div>
                    <input
                      id="file-input"
                      type="file"
                      accept="image/*"
                      onChange={(e) => setFile(e.target.files[0])}
                      className="hidden"
                      data-testid="file-input"
                    />
                    <div>
                      <Label>Your Name *</Label>
                      <Input
                        placeholder="Enter your name"
                        value={uploader}
                        onChange={(e) => setUploader(e.target.value)}
                        required
                        data-testid="uploader-input"
                      />
                    </div>
                    <div>
                      <Label>Tags (comma-separated)</Label>
                      <Input
                        placeholder="nature, landscape, urban"
                        value={tags}
                        onChange={(e) => setTags(e.target.value)}
                        data-testid="tags-input"
                      />
                    </div>
                    <div>
                      <Label>Description</Label>
                      <Input
                        placeholder="Add a description"
                        value={description}
                        onChange={(e) => setDescription(e.target.value)}
                        data-testid="description-input"
                      />
                    </div>
                    <Button type="submit" disabled={uploading} className="w-full rounded-full" data-testid="submit-upload-button">
                      {uploading ? "Uploading..." : "Upload Image"}
                    </Button>
                  </form>
                </DialogContent>
              </Dialog>
            </div>
          </div>
        </div>
      </header>

      {/* Gallery */}
      <main className="max-w-[1800px] mx-auto px-6 md:px-12 lg:px-20 py-12">
        {loading ? (
          <div className="text-center py-20" data-testid="loading-indicator">
            <p className="text-lg text-muted-foreground font-sans">Loading gallery...</p>
          </div>
        ) : filteredImages.length === 0 ? (
          <div className="text-center py-20" data-testid="empty-gallery">
            <p className="text-lg text-muted-foreground font-sans mb-4">No images yet</p>
            <Button onClick={() => setUploadOpen(true)} className="rounded-full" data-testid="empty-upload-button">
              Upload Your First Image
            </Button>
          </div>
        ) : (
          <div className="masonry-grid" data-testid="gallery-grid">
            {filteredImages.map((image) => (
              <div key={image.id} className="masonry-item" data-testid={`image-card-${image.id}`}>
                <Card className="image-card relative overflow-hidden cursor-pointer group border-0 shadow-[0_8px_30px_rgb(0,0,0,0.04)] hover:shadow-[0_8px_30px_rgb(0,0,0,0.12)] transition-all duration-300">
                  <img
                    src={`${BACKEND_URL}${image.url}`}
                    alt={image.filename}
                    className="w-full h-auto object-cover"
                    onClick={() => { setSelectedImage(image); setViewerOpen(true); }}
                    data-testid={`image-${image.id}`}
                  />
                  <div className="image-overlay flex items-end justify-between p-4">
                    <div className="text-white flex-1">
                      <p className="font-medium mb-1 text-sm" data-testid={`image-uploader-${image.id}`}>{image.uploader}</p>
                      {image.tags.length > 0 && (
                        <div className="flex gap-1 flex-wrap">
                          {image.tags.map((tag, idx) => (
                            <Badge key={idx} variant="secondary" className="text-xs bg-white/20 text-white border-0" data-testid={`image-tag-${image.id}-${idx}`}>
                              {tag}
                            </Badge>
                          ))}
                        </div>
                      )}
                    </div>
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        variant="secondary"
                        className="rounded-full bg-white/90 hover:bg-white"
                        onClick={(e) => { e.stopPropagation(); handleDownload(image); }}
                        data-testid={`download-button-${image.id}`}
                      >
                        <Download className="w-4 h-4" />
                      </Button>
                      <Button
                        size="sm"
                        variant="destructive"
                        className="rounded-full"
                        onClick={(e) => { e.stopPropagation(); handleDelete(image.id); }}
                        data-testid={`delete-button-${image.id}`}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                </Card>
              </div>
            ))}
          </div>
        )}
      </main>

      {/* Image Viewer */}
      <Dialog open={viewerOpen} onOpenChange={setViewerOpen}>
        <DialogContent className="max-w-[90vw] max-h-[90vh] p-0 border-0 overflow-hidden backdrop-blur-gallery" data-testid="image-viewer-dialog">
          {selectedImage && (
            <div className="relative">
              <Button
                variant="secondary"
                size="sm"
                className="absolute top-4 right-4 z-10 rounded-full bg-white/90 hover:bg-white"
                onClick={() => setViewerOpen(false)}
                data-testid="close-viewer-button"
              >
                <X className="w-4 h-4" />
              </Button>
              <img
                src={`${BACKEND_URL}${selectedImage.url}`}
                alt={selectedImage.filename}
                className="w-full h-auto max-h-[80vh] object-contain"
                data-testid="viewer-image"
              />
              <div className="p-6 bg-white border-t border-border">
                <h3 className="font-serif text-2xl mb-2" data-testid="viewer-filename">{selectedImage.filename}</h3>
                <div className="flex items-center gap-4 text-sm text-muted-foreground mb-3">
                  <span className="flex items-center gap-1" data-testid="viewer-uploader">
                    <User className="w-4 h-4" />
                    {selectedImage.uploader}
                  </span>
                  <span data-testid="viewer-date">
                    {new Date(selectedImage.upload_date).toLocaleDateString()}
                  </span>
                  <span data-testid="viewer-size">
                    {(selectedImage.file_size / 1024).toFixed(2)} KB
                  </span>
                </div>
                {selectedImage.description && (
                  <p className="text-sm mb-4" data-testid="viewer-description">{selectedImage.description}</p>
                )}
                {selectedImage.tags.length > 0 && (
                  <div className="flex gap-2 flex-wrap mb-4" data-testid="viewer-tags">
                    {selectedImage.tags.map((tag, idx) => (
                      <Badge key={idx} variant="secondary" data-testid={`viewer-tag-${idx}`}>{tag}</Badge>
                    ))}
                  </div>
                )}
                <div className="flex gap-3">
                  <Button
                    onClick={() => handleDownload(selectedImage)}
                    className="flex-1 rounded-full"
                    data-testid="viewer-download-button"
                  >
                    <Download className="w-4 h-4 mr-2" />
                    Download
                  </Button>
                  <Button
                    variant="destructive"
                    onClick={() => handleDelete(selectedImage.id)}
                    className="flex-1 rounded-full"
                    data-testid="viewer-delete-button"
                  >
                    <Trash2 className="w-4 h-4 mr-2" />
                    Delete
                  </Button>
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Gallery;