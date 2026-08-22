import { useMutation } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { apiClient } from "@/lib/api";
import { errMessage } from "@/lib/utils";
import { WEBSITE_TYPES } from "@/lib/types";

export function NewWebsitePage() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [websiteType, setWebsiteType] = useState("other");
  const [industry, setIndustry] = useState("");
  const [targetAudience, setTargetAudience] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: apiClient.createWebsite,
    onSuccess: (website) => {
      navigate(`/websites/${website.id}`);
    },
    onError: (err) => setError(errMessage(err)),
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    create.mutate({
      name: name.trim(),
      url: url.trim(),
      website_type: websiteType,
      industry: industry.trim() || null,
      target_audience: targetAudience.trim() || null,
      description: description.trim() || null,
    });
  }

  return (
    <div className="mx-auto max-w-xl space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Add a website</h1>
        <p className="mt-1 text-sm text-slate-500">
          Wiseweb-AI performs a <strong>passive, public-only</strong> analysis. Log in,
          then scan from the website page.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Website details</CardTitle>
          <CardDescription>All fields help the analyzers give better context.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSubmit} className="space-y-4">
            {error && <Alert variant="error">{error}</Alert>}
            <div>
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                required
                maxLength={255}
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Acme Widgets"
              />
            </div>
            <div>
              <Label htmlFor="url">URL</Label>
              <Input
                id="url"
                required
                type="url"
                maxLength={2048}
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://example.com"
              />
              <p className="mt-1 text-xs text-slate-500">
                We'll normalize it automatically (https://example.com â†’ https://example.com/).
              </p>
            </div>
            <div>
              <Label htmlFor="type">Website type</Label>
              <Select id="type" value={websiteType} onChange={(e) => setWebsiteType(e.target.value)}>
                {WEBSITE_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t.charAt(0).toUpperCase() + t.slice(1)}
                  </option>
                ))}
              </Select>
            </div>
            <div>
              <Label htmlFor="industry">Industry</Label>
              <Input
                id="industry"
                maxLength={128}
                value={industry}
                onChange={(e) => setIndustry(e.target.value)}
                placeholder="e.g. SaaS, E-commerce"
              />
            </div>
            <div>
              <Label htmlFor="audience">Target audience</Label>
              <Input
                id="audience"
                maxLength={255}
                value={targetAudience}
                onChange={(e) => setTargetAudience(e.target.value)}
                placeholder="e.g. Small business owners"
              />
            </div>
            <div>
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                maxLength={1024}
                rows={3}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="What does the site do?"
              />
            </div>
            <div className="flex gap-2 pt-2">
              <Button type="submit" loading={create.isPending}>
                Add website
              </Button>
              <Button asChild variant="outline">
                <Link to="/websites">Cancel</Link>
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
