# Fase 4: BCF Export

## Doel
Export validatie issues als BCF file voor gebruik in BIM software.

## Specs

### Spec 4.1 - BCF 2.1 Generator
- `engine/bcf_generator.py`
- BCF 2.1 specificatie implementatie
- Structuur:
  ```
  bcf.zip/
  ├── bcf.version
  ├── extensions.xml (optional)
  └── {guid}/
      ├── markup.bcf
      ├── viewpoint.bcfv
      └── snapshot.png
  ```
- UUID generatie voor topics
- Proper XML encoding

### Spec 4.2 - Viewpoint Generation
- Camera positie berekenen voor element
- Bounding box bepaling
- Optimal viewing angle algoritme
- Components sectie met:
  - Selection (gefaald element)
  - Visibility (context elementen)
- Orthogonal en perspective support

### Spec 4.3 - Issue Mapping
- Map ValidationResult naar BCF Topics
- Topic velden:
  - `Title` - Korte beschrijving van fout
  - `Description` - Gedetailleerde uitleg
  - `Priority` - Gebaseerd op IDS severity
  - `Type` - "IDS Validation"
  - `Status` - "Open"
  - `AssignedTo` - Leeg (user fills in)
- Labels voor categorisatie
- Reference links naar IDS spec

### Spec 4.4 - Download Endpoint
- `GET /api/v1/results/{job_id}/bcf`
- Genereer BCF on-demand
- Stream response voor grote files
- Content-Disposition header voor download
- Caching van gegenereerde BCF files

### Spec 4.5 - Integration Tests
- Test BCF import in:
  - BIMcollab (primary)
  - Solibri
  - Navisworks
- Valideer viewpoint correctheid
- Verify issue data integriteit

## Exit Criteria
- [ ] BCF file importeerbaar in BIMcollab
- [ ] Viewpoint toont gefaald element
- [ ] Issue title/description zinvol
- [ ] Batch export van meerdere issues

## BCF Structure Details

### bcf.version
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Version VersionId="2.1" xsi:noNamespaceSchemaLocation="version.xsd">
  <DetailedVersion>2.1</DetailedVersion>
</Version>
```

### markup.bcf
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Markup>
  <Header>
    <File IfcProject="{project_guid}" isExternal="false">
      <Filename>model.ifc</Filename>
    </File>
  </Header>
  <Topic Guid="{topic_guid}" TopicType="IDS Validation">
    <Title>Missing FireRating property</Title>
    <Description>Element IfcWall (GlobalId: 2O2Fr$t4X7Zf8NOew3FL9r)
    does not have required property 'FireRating' in Pset_WallCommon.</Description>
    <Priority>High</Priority>
    <CreationDate>2024-01-15T10:30:00Z</CreationDate>
    <CreationAuthor>IFC Validator</CreationAuthor>
    <ModifiedDate>2024-01-15T10:30:00Z</ModifiedDate>
    <ModifiedAuthor>IFC Validator</ModifiedAuthor>
    <Labels>
      <Label>IDS</Label>
      <Label>Property Missing</Label>
    </Labels>
  </Topic>
  <Viewpoints>
    <ViewPoint Guid="{viewpoint_guid}">
      <Viewpoint>viewpoint.bcfv</Viewpoint>
      <Snapshot>snapshot.png</Snapshot>
    </ViewPoint>
  </Viewpoints>
</Markup>
```

### viewpoint.bcfv
```xml
<?xml version="1.0" encoding="UTF-8"?>
<VisualizationInfo Guid="{viewpoint_guid}">
  <Components>
    <Selection>
      <Component IfcGuid="2O2Fr$t4X7Zf8NOew3FL9r"/>
    </Selection>
    <Visibility DefaultVisibility="true">
      <Exceptions/>
    </Visibility>
  </Components>
  <PerspectiveCamera>
    <CameraViewPoint>
      <X>10.5</X>
      <Y>5.2</Y>
      <Z>3.0</Z>
    </CameraViewPoint>
    <CameraDirection>
      <X>-0.7</X>
      <Y>-0.5</Y>
      <Z>-0.3</Z>
    </CameraDirection>
    <CameraUpVector>
      <X>0</X>
      <Y>0</Y>
      <Z>1</Z>
    </CameraUpVector>
    <FieldOfView>60</FieldOfView>
  </PerspectiveCamera>
</VisualizationInfo>
```

## API Signatures

```python
# engine/bcf_generator.py

class BCFGenerator:
    def __init__(self, validation_result: ValidationResult):
        self.result = validation_result

    def generate(self) -> bytes:
        """Generate BCF zip file as bytes."""

    def _create_topic(self, element_result: ElementResult) -> Topic:
        """Create BCF topic from validation element result."""

    def _create_viewpoint(
        self,
        element: ElementResult,
        camera_position: CameraPosition
    ) -> Viewpoint:
        """Create viewpoint for element."""

    def _calculate_camera(
        self,
        bounding_box: BoundingBox
    ) -> CameraPosition:
        """Calculate optimal camera position for element."""

class Topic(BaseModel):
    guid: UUID
    title: str
    description: str
    priority: str
    topic_type: str = "IDS Validation"
    status: str = "Open"
    labels: list[str]
    creation_date: datetime
    creation_author: str = "IFC Validator"

class Viewpoint(BaseModel):
    guid: UUID
    camera: PerspectiveCamera | OrthogonalCamera
    components: Components
```

## Frontend Integration

```typescript
// Download BCF button in results view
const downloadBCF = async (jobId: string) => {
  const response = await fetch(`/api/v1/results/${jobId}/bcf`);
  const blob = await response.blob();

  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `validation-${jobId}.bcf`;
  a.click();
  window.URL.revokeObjectURL(url);
};
```
